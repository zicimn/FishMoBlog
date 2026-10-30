# 管理端（`admin/`）

Nuxt 4 + Tailwind v4 + Pinia + Tiptap，**纯 SPA（`ssr: false`）**，`srcDir = app/`，dev 端口 **3001**。**不部署线上**，只在本机使用。

管理端只做四件事：文章（列表 / 新建 / 编辑）、评论管理、留言管理、用户查看。接口全部来自 `app/`，没有 BFF。

## 配置

```ts
// admin/nuxt.config.ts
devServer: { port: 3001 },
modules: ['@pinia/nuxt'],
runtimeConfig: { public: { apiBase: 'http://127.0.0.1:8000' } },
ssr: false,
```

- `apiBase` **硬编码** `http://127.0.0.1:8000`（可用 `NUXT_PUBLIC_API_BASE` 覆盖）。因为只在本机跑，所以不需要像 web 那样区分 SSR/浏览器两个地址。
- 后端 `CORS_ORIGINS` 必须包含 `http://localhost:3001`，否则浏览器直接拦跨源请求。
- `ssr: false`：令牌在 localStorage，SSR 读不到，开了 SSR 只会让首屏闪一下未登录态；管理端不需要 SEO。

## 页面

| 路由 | 文件 | 说明 |
| :--- | :--- | :--- |
| `/` | `pages/index.vue` | 直接 `navigateTo('/articles', { replace: true })`，没有独立仪表盘 |
| `/login` | `pages/login.vue` | 登录 |
| `/articles` | `pages/articles/index.vue` | 文章列表（筛选、搜索、预览、删除） |
| `/articles/new` | `pages/articles/new.vue` | 新建（默认状态 = 草稿 3） |
| `/articles/[id]/edit` | `pages/articles/[id]/edit.vue` | 编辑 |
| `/comments` | `pages/comments/index.vue` | 评论管理（含回复，扁平） |
| `/messages` | `pages/messages/index.vue` | 留言管理 |
| `/users` | `pages/users/index.vue` | 用户列表（只读） |

导航在 `layouts/default.vue`，用 `NuxtLink` + 当前路由高亮。

## 登录与鉴权

### `stores/auth.ts`（Pinia）

- localStorage 键：`blog_admin_token` / `blog_admin_user`。
- 用户快照只存 `email` / `username` / `is_admin` 三个字段（管理端只需要展示与权限判断）。
- `restore()` 在 store 创建时立即执行，刷新页面后保持登录态。
- `login()` 调 `/auth/login`，从响应体 `data.access_token` 取令牌。
- `logout()` 无论后端成败都 `clear()`：后端 Redis 故障对登出“失败关闭”会回 403，不清本地会让用户卡在“以为登出了、令牌其实还在”的状态。

### `middleware/auth.global.ts`

只是 **UI 便利**：未登录跳 `/login`，已登录不停在登录页。真正的权限校验在后端 `/admin` 分组的 `GetAdminUser`。

> 注意：登录页成功后 `navigateTo(...)` 的三元两边都是 `/articles`。**非管理员也能登录成功**，只是之后所有 `/admin/*` 请求会 403。当前没有“非管理员禁止登录”的前端拦截，属既有行为。

## 唯一 HTTP 出口 `useApi.ts`

`composables/useApi.ts` 是全管理端唯一的 HTTP 出口：

- 自动带 `Authorization: Bearer <token>`。
- `baseURL = config.public.apiBase`。
- **解信封**：只有响应同时含 `data` 和 `code` 才拆 `{msg, code, data}`，返回 `data`；否则原样返回。这是为了兼容 `GET /admin/article/{id}` 的裸 dict（`to_admin_detail` 没有信封）。无条件取 `res.data` 会让编辑页 `initial` 变成 `undefined`，整块表单不渲染。
- **错误**：`detail` 是字符串直接用；是数组（422）就把各条 `msg` 拼起来；否则用 ofetch 的 `message`。
- **401**：清本地态并 `navigateTo('/login')`，否则用户会对着一个永远 401 的界面反复点。
- **`del` 支持 query**：删图接口的 `public_id` 形如 `fishmo_upload/abc`（含斜杠），做不了路径参数，只能走查询串。`$fetch` 的 query 会自动 encode。

`describeError` 按状态码兜底：409 优先于 500 区分（slug 撞车现在明确回 409 且带中文 detail），403 → “需要管理员权限”，429 → “操作过于频繁”，401 → “登录已失效”，0 → “连不上后端服务”。

## 用到的接口

| 用途 | 接口 |
| :--- | :--- |
| 登录 / 登出 | `POST /auth/login`、`POST /auth/logout` |
| 文章 | `GET /admin/article/list`、`POST /admin/article/save`、`PUT /admin/article/edit/{id}`、`DELETE /admin/article/remove/{id}`、`GET /admin/article/{id}` |
| 图片 | `POST /admin/upload/image`、`DELETE /admin/upload/image?public_id=` |
| 评论 | `GET /admin/comment/list`、`DELETE /comments/{id}` |
| 留言 | `GET /msg/list`（分页参数 **`p`**）、`DELETE /msg/del?id=` |
| 用户 | `GET /admin/user/list`（只读，不含 `password_hash`） |

注意 `GET /msg/list` 与 `DELETE /msg/del` 是**共用接口**，不是 `/admin` 前缀；分页参数是 `p` 不是 `page`。

## 文章列表

- 查询参数 `page` / `size` / `status` / `keyword`（`category_name` 后端支持，当前页面未使用）。
- 筛选条件同步到 URL query；`keyword` 有 350ms 防抖。
- `status` 取值：`1` 正常 / `2` 隐藏 / `3` 草稿。
- 列表接口 `to_admin_preview` **不含 `content`**。点“预览”时按需再发一次 `GET /admin/article/{id}`，并用递增序号 `seq` 丢弃过期响应（快速连点不同文章时不会显示错内容）。**不要给列表加批量预取**。
- 删除走 `DELETE /admin/article/remove/{id}`，确认弹窗；删掉当前页最后一条时自动回上一页。
- 空列表是正常业务结果，走空态，不报错。

## 文章表单与图片三态

`ArticleForm.vue` 负责提交编排，`RichTextEditor.vue` 负责正文与占位图，`useImageUpload.ts` 是**唯一**的上传入口（类型/体积校验、base64 转换、错误文案只有一份）。

### 表单语义

- 新建默认 `status = 3`（草稿）：管理端最怕手滑把半成品发出去，想发布要显式选“正常”。
- 前端先校验：标题必填、`path` 必填且只允许 `[A-Za-z0-9_-]`（DB 是 NOT NULL + 唯一）、正文不能为空。
- **编辑**走 `ArticleEditRequest` 的 `model_fields_set` 语义：可空字段（`description` / `cover` / `cover_public_id`）一律“**发键 + null 或新值**”，让“表单显示什么，库里就是什么”成立。`category_name` 留空 = 不修改（详情接口只回 `category_id`，不回名字，编辑页这一栏本来就是空的）。
- **新建**走 `ArticleSaveRequest`：`description` / `content` / `category_name` 是必填字符串，空串在 Pydantic 层合法；`cover` 可选，空串由后端归一成 NULL。

### 三态契约

选图阶段**只做本地预览**（`URL.createObjectURL`），真正上传发生在点提交时。`ArticleForm` 暴露：

| 方法 | 页面调用时机 | 行为 |
| :--- | :--- | :--- |
| `flushPendingImages()` | 提交前（内部调用编辑器的同名方法） | 上传正文占位图并替换成真 URL；返回 `false` 必须中断提交 |
| `commitUploads()` | 请求成功后 | 释放本地占位与预览 |
| `rollbackUploads()` | 请求失败后 | 删掉本次刚上传的封面/正文图，还原表单与正文 |

页面（`articles/new.vue` / `articles/[id]/edit.vue`）的 `onSubmit`：

```ts
try {
  const data = await api.post('/admin/article/save', payload)
  formRef.value?.commitUploads()
  navigateTo(`/articles/${data.id}/edit`)
} catch (err) {
  await formRef.value?.rollbackUploads()
  // 409 → slug 撞车
}
```

`onSubmit` 里上传成功后**不能提前 `dropPendingCover()`**：本地文件与预览要留到保存成功，否则保存失败就没法回滚，用户每重试一次就在云端多留一张孤儿图。

### 正文占位图

- `RichTextEditor` 用 `PendingImage extends ImageExtension`，在 `addAttributes` 里**声明 `data-pending-upload`**。ProseMirror 只保留 schema 里声明过的 attr，只在 `insertContent` 里塞属性是没用的。
- 占位图是 `<img src="blob:..." data-pending-upload="k1">`；`flushPendingImages()` 上传后把 `src` 换成 Cloudinary URL、清掉标记。
- `allowBase64: false`，正文不接受 base64 内联图。
- 后端 `schemas/article.py` 的 `_reject_pending_images` 是最后一道闸：漏 flush 时返回 422，而不是把 `blob:` 写进库。
- 正文插图缩放用 `@tiptap/extension-image` 内置的 `resize`（`ResizableNodeView`），松手时把 `width`/`height` 写回节点属性随 HTML 入库。**手柄是裸 `div`，必须在 `assets/css/main.css` 里写 `[data-resize-handle]` 相关样式才看得见。**

### `useImageUpload.ts`

- `MAX_IMAGE_BYTES = 5MB`；只接受 `file.type.startsWith('image/')`。
- `upload(file)`：FileReader 转 data-URL → `POST /admin/upload/image`，返回 `{url, public_id}` 或 `null`（错误写进 `error`）。
- `remove(publicId)`：`DELETE /admin/upload/image?public_id=`，**失败静默**（云端残留不影响继续编辑）。
- 前端 5MB 只是为了省一次注定失败的上传；真正的上限在服务端（解压前 5MB + 25M 像素）。

## 预览与前台样式

- 列表预览用 `ArticlePreview.vue`，它**刻意复制了前台详情页的排版与玻璃拟态样式**。改前台详情页样式时必须同步改它，否则后台预览与线上不一致。
- 预览只基于当前表单/列表数据，**不触发任何上传**、不调 `commitUploads` / `rollbackUploads`。
- 正文用 `v-html` 渲染原始 HTML（文章正文后端不消毒，仅管理员可写）。
- 列表预览点“预览”才发详情请求；表单页的“预览”用当前草稿（未保存的正文/封面可能是 `blob:`，同一浏览器会话内可渲染）。

## 评论、留言、用户页

- **评论**：`GET /admin/comment/list`，扁平列表含回复，状态 `0 待审核 / 1 正常 / 2 屏蔽`，可按状态筛。删除走 `DELETE /comments/{id}`（作者或管理员，级联删子孙）。内容用 `v-html` 渲染（后端消毒过）。
- **留言**：`GET /msg/list`（`p` 分页），删除 `DELETE /msg/del?id=`。内容同样是消毒过的 HTML。
- **用户**：`GET /admin/user/list`，只读。`user.status` 是 `0 禁用 / 1 正常`，**不能复用评论页的状态映射**。`bio` 是纯文本，模板里用插值而不是 `v-html`。列表不含 `password_hash`。
- 三个列表都做了 URL query 同步与“删最后一条回上一页”。

## 构建注意

```bash
cd admin && npm run dev     # :3001
cd admin && npm run build   # 产物在 admin/.output/
```

- `admin/nuxt.config.ts` **没有**开 `typescript.typeCheck`，`npm run build` **不跑类型检查**，只能证明“能构建”。
- 管理端没有 `typecheck` 脚本。
- **不要在 dev 服务运行时跑 `npm run build`**：构建与 dev 共用 `node_modules/.cache/nuxt/.nuxt`，构建结束会触发 dev 重启，已打开页面会因旧模块 URL 失效报 `Failed to fetch dynamically imported module`。要验构建先停 dev。
- 管理端**不部署**，所以不存在线上旧构建问题；线上相关排查见 `deploy.md`。