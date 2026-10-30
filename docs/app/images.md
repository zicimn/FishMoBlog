# 图片上传与清理（Cloudinary）

这是前后端协作最复杂的一块。改之前先读完本文。链路由五处协作组成：

```text
utils/cloudinary.py   转换 / 上传 / 销毁 / URL 反推 public_id
  → services/image.py 业务编排（线程池、错误泛化、命名空间白名单）
  → api/admin.py      两个端点（POST 上传 / DELETE 按 query 删）
  → schemas/image.py + schemas/article.py   入参与防漏闸
  → admin/app/composables/useImageUpload.ts + ArticleForm.vue + RichTextEditor.vue
```

## 为什么有 `cover_public_id` 列

`cover` 只存 URL 的话，换封面/删文章时无法定位云端资源——从 URL 反推 `public_id` 依赖拼接规则，随时会失效。所以 `article.cover_public_id` 存云端唯一标识，作为**清理凭据**。正文里的插图没有逐图列，只能靠 URL 反推（见后文）。

## 端点位置与形态

- 两个端点都在 `api/admin.py`，**不要挪到 `api/article.py`**：后者是公开无鉴权的读路由，挂上去就是匿名可用的上传口（刷爆配额、变免费图床）。管理端 router 级 `GetAdminUser` 已覆盖。
- 传输是 **base64 JSON**（`ImageUploadRequest.image`），刻意不引 multipart——前端 `useApi` 只有 JSON body 通道。
- `public_id` 形如 `fishmo_upload/abc` **含斜杠**，所以删除走 **query 参数** `?public_id=`，不能放路径参数。
- 上传端点**不限流**：发布端只有管理员在用，账号可信。残余风险：令牌泄露即可无限量上传刷配额，补偿手段是 Cloudinary 用量告警与令牌轮换。

## 后端四道闸（`utils/cloudinary.py`）

顺序不能改：

1. **base64 文本长度闸**：`MAX_IMAGE_B64_CHARS = (5MB * 4) // 3 + 1024`，在 `b64decode` **之前**检查。base64 比原始字节多 1/3，不前置拦截的话，巨大字符串会先被完整解码进内存（峰值约为请求体的 2.75 倍），后面的 5MB 字节检查根本来不及拦。
2. **解码后 5MB 字节闸**：`MAX_IMAGE_BYTES = 5 * 1024 * 1024`。
3. **25M 像素闸**：`MAX_IMAGE_PIXELS = 25_000_000`，并且**必须同时赋给 `Image.MAX_IMAGE_PIXELS`**。否则这个常量只是一道事后手写检查：PIL 默认约 89.5M，且 89.5M~178M 之间只发 `DecompressionBombWarning`、默认不抛。配合 `warnings.simplefilter("error", Image.DecompressionBombWarning)` 把炸弹挡在真正解码前；`img.load()` 强制在 `try` 内解完整个位图，避免损坏文件把异常拖到后面、报错位置失真。
4. **失败一律泛化**：`convert_image_to_webp` / `upload_image_to_cloudinary` 失败返回 `None`，真实原因只进日志。Cloudinary SDK 异常消息里带原始响应体与请求 URL，透传等于泄露 `cloud_name` 与内部参数。

### 转换细节

- 带透明通道的模式（`RGBA` / `LA` / `PA`，或带 `transparency` 的 `P`）转 `RGBA`，否则透明区变黑块；其余转 `RGB`。
- `thumbnail((800, 800), LANCZOS)` 等比缩到不超过 800×800。
- 输出 WEBP，`quality=85`、`method=6`、`lossless=False`。
- 返回的是 **base64 文本**，调用方自己拼 data-URI。

### 为什么必须走线程池

Cloudinary SDK 是**同步 urllib3**，PIL 解码也是同步阻塞。`services/image.py` 的 `Upload` / `Delete` 都把调用包进 `run_in_threadpool`。直接在协程里调用会卡住整个事件循环，表现为“上传期间所有接口一起变慢”。上传/销毁超时统一 15 秒，避免线程池工作线程长期挂死。

## 销毁与清理

### `destroy_image` 不抛异常

云端清理失败只 `logger.warning`，返回 `False`。调用方是“换封面 / 删文章”这类主操作，清理失败不该把主操作带崩——残留一张孤儿图可接受，运维侧补偿。

### `ImageService.Delete` 只删本应用命名空间

`public_id` 由前端回传，Cloudinary 账号可能同时托管别的资源。不加校验等于“任何管理员都能删账号内任意资产”。所以只允许 `fishmo_upload/` 前缀；空值/跨命名空间只告警、不动手，并且**幂等返回成功**（调用方此时已不再引用这张图，回错只会让用户重试一个不可能成功的操作）。

### 清理顺序：先 commit，后销毁

`ArticleService.Remove` / `Edit` 都是：

1. 记下旧封面 `public_id`、旧封面 URL、旧正文里的 `<img src>`；
2. 提交数据库变更（删除或更新）；
3. commit 成功后，才尽力销毁不再被引用的云端图。

顺序不能反。反过来（先删图再提交）一旦 commit 失败回滚，就是“库里有文章、图已删”，前台裂图且无法自愈。

清理前还要做**引用检查**（`_is_still_referenced`）：同一张图可能被本篇文章正文、其他文章正文、或其他文章封面复用。只按本文差集删会误删别人还在用的图。检查用 `Article.content.contains(src, autoescape=True) OR Article.cover == src`，此时本文的新内容已提交（删文场景整行已删），命中的只可能是别的文章。

### `public_id_from_url`：三重归属

正文只存 URL，编辑/删除时靠它反推 `public_id`。为免误删，必须同时满足：

1. 主机是 `res.cloudinary.com`；
2. 路径属于本账号（`/<cloud_name>/image/upload/`）；
3. `public_id` 落在本应用的 `fishmo_upload/` 命名空间下。

另外拒绝含 `\` 的路径、空段、`.`、`..`，防止 `%2F` 编码穿越绕过第 3 条。只认标准图片扩展名（`avif/gif/jpe?g/png/svg/webp`），扩展名从 `public_id` 末尾剥掉。

**它不能取代数据库里的 `public_id` 列**（封面仍用 `cover_public_id`），只服务“尽力清理孤儿图”，失败返回 `None` 即放弃。

## 前端三态契约（关键）

选图阶段**只做本地预览**（`URL.createObjectURL`），真正上传发生在点提交时。`RichTextEditor` / `ArticleForm` 暴露三个方法，由页面在 `try/catch` 里驱动：

| 方法 | 时机 | 行为 |
| :--- | :--- | :--- |
| `await flushPendingImages()` | 提交前 | 上传正文占位图并替换成真 URL；返回 `false` 表示有图没传成，**必须中断提交** |
| `commitUploads()` | 请求成功 | 云端图已被正文引用，释放本地占位与预览 |
| `await rollbackUploads()` | 请求失败 | 删掉本次刚上传的图、把正文还原成占位图、还原表单 |

页面顺序：

```ts
const flushed = await formRef.value.flushPendingImages()
if (!flushed) return                 // 上传失败，中断提交

try {
  await api.post(...)                // 保存文章
  formRef.value.commitUploads()
} catch {
  await formRef.value.rollbackUploads()
}
```

### 为什么上传成功后不能提前 `dropPendingCover()`

本地文件与预览 URL 要留到**保存成功**。提前释放的话，保存失败就没法回滚，用户每重试一次就在云端多留一张孤儿图。`commitUploads()` 成功后才 `dropPendingCover()`；`rollbackUploads()` 会用 `remove(public_id)` 删掉本次新上传的封面。

### 正文占位标记必须进 ProseMirror schema

正文占位图是 `<img src="blob:..." data-pending-upload="k1">`。`data-pending-upload` **必须声明进 ProseMirror schema**（`ImageExtension.extend({ addAttributes })`）——只往 `insertContent` 里塞属性是没用的，ProseMirror 只保留 schema 里声明过的 attr，渲染出的 HTML 里没有标记就再也定位不到占位图。

### 后端防漏闸 `_reject_pending_images`

`schemas/article.py` 对 `content` 和 `cover` 挂了校验器：万一哪条路径漏了 flush，就让请求 **422**，而不是把 `blob:` 地址写进库（blob URL 只对创建它的浏览器会话有效，前台必然 404 且事后修不回来）。

判据分两种形态：

- **正文（HTML 片段）**：看**属性形态**（`data-pending-upload` 或 `src="blob:` / `src='blob:`）。刻意不用“出现 `blob:` 就拒”——一篇讲 objectURL 的文章在代码块里正常带着这个词会被误伤。
- **封面（裸 URL）**：看 **scheme 前缀**（`lstrip().lower().startswith("blob:")`）。

`ImageUploadRequest.image` 还有 Pydantic 的 `max_length = 8 * 1024 * 1024` 作为服务端兜底；真正更严的前置闸是 `utils/cloudinary.MAX_IMAGE_B64_CHARS`（约 7.0M 字符）。

## 编辑器缩放

正文插图用 `@tiptap/extension-image` 内置的 `resize`（`ResizableNodeView`），松手时把 `width` / `height` 写回节点属性随 HTML 入库。手柄是裸 `div`，**必须在 `admin/app/assets/css/main.css` 里写 `[data-resize-handle]` 相关样式才看得见**。前台用 `max-width:100%; height:auto` 兜窄屏。

## 已知残余

- 提交请求在飞的过程中用户关掉标签页：上传可能已完成，但保存请求没到后端，云端留下孤儿图。
- 非本应用标准 URL 形态的图（外链、别的命名空间、带复杂变换段）无法反推 `public_id`，不会被清理。
- 没有定期扫描 Cloudinary 的 sweep（不做离线对账）。
- 文章正文存的是**未消毒的原始 HTML**，`sanitize_html` 只用于评论与留言，且白名单刻意不含 `img`。目前只有管理员能写文章，风险有限；若日后要消毒正文，需做 `img` + `res.cloudinary.com` 域白名单，而不是直接放开 `img`。