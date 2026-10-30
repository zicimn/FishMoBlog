# 文章与栏目（`services/article.py` / `services/category.py`）

文章是后端的核心业务。前台读、后台写，两个入口共用同一个 `ArticleService`，靠方法参数区分语义。返回结构全部是 `schemas/article.py` 里的 `to_xxx()` 拼的裸 dict。

## 方法一览

| 方法 | 调用方 | 作用 |
| :--- | :--- | :--- |
| `GetList(page, size, category_name)` | 前台 `GET /article/` | 只查 `STATUS_PUBLIC`，返回 `{total, items}` |
| `GetSlug(path)` | 前台 `GET /article/{path}` | 按 slug 查可见文章，**并自增浏览量** |
| `GetId(id, status=False)` | 后台 `GET /admin/article/{id}` | 按数字 id 查；`status=True` 时放开可见性过滤 |
| `AdminList(page, size, status, keyword, category_name)` | 后台列表 | 不筛可见性，可按状态/关键词/栏目筛 |
| `Save(data)` | 后台新建 | 查重 → `GetOrSave` 栏目 → 插入 → commit |
| `Edit(id, data)` | 后台编辑 | `model_fields_set` 语义更新，提交后清理旧图 |
| `Remove(id)` | 后台删除 | 记录封面/正文图片 → 删除 → commit → 清理云端 |

## 状态过滤：`status` 参数的语义

`GetId(id, status=False)` 的参数**不是“按状态查”**，而是“**是否放开状态过滤**”：

- `False`（默认）＝ 前台语义，只认 `STATUS_PUBLIC`（即 `1`）；
- `True` ＝ 后台语义，不做状态过滤，管理员才能读到隐藏/草稿。

调用方只有 `api/admin.py` 一处传 `True`，默认值保证前台行为不变。

`GetSlug` 则**始终**过滤 `Article.status.in_(STATUS_PUBLIC)`，所以隐藏/草稿文章无法通过前台 slug 访问。

### `noload(Article.category)`

两个详情查询都带 `.options(noload(Article.category))`。原因：

- 详情不需要栏目关系数据，避免 ORM 额外打一条 `selectin` 查询；
- `to_admin_detail` **刻意不返回分类名**，因为异步 session 下访问 `article.category.name` 会触发懒加载并直接报错。前端需要名字时用 `category_id` 自己映射。
- 不要写 `noload(Article.columns)`：专栏功能已删，`Article` 上已无 `columns` 关系，引用会在构造查询时 `AttributeError`。

## 浏览量：`GetSlug` 会自增

`GetSlug` 的流程是：

```python
await ArticleViewCounter.incr(result.id)
data = to_detail(result)
data["views"] = await ArticleViewCounter.get_total(result.id, result.views)
```

- 详情页每访问一次计一次，刷新/来回导航都会 +1。这是既有行为，**不要在 web 侧加“只看一次”的计数**。
- `incr` 内部对 Redis 故障降级（返回 0），不会让详情页 500。
- `get_total` 是 `async`，**漏 `await` 会把 coroutine 塞进响应体，序列化直接 500**。

> 只有 `GetSlug` 自增，按数字 id 的 `GetId` **不自增**。任何新接口都不要复用 `GetSlug` 做只读展示，否则会刷高浏览量——评论列表就是因为复用过它，后来改成了自己的只读解析（`ComService.GetList`）。

## 列表查询

### 前台 `GetList`

- 过滤 `Article.status.in_(STATUS_PUBLIC)`。
- `category_name` 用 **falsy 判断**（`if category_name:`），空串不加过滤。
- 栏目解析走 `CatService.GetByName`（**只读**）。未命中直接返回空列表，**不顺手建栏目**——GET 不该写库，也不能把 `None` 当有效 id 去匹配 `category_id IS NULL`。
- 排序 `created_at DESC`，`offset/limit` 分页。

### 后台 `AdminList`

与前台同构，差异：

1. **不加可见性过滤**——后台必须能看到隐藏与草稿，否则管理端半个盲区。
2. 支持 `status` 精确筛选、`keyword` 标题模糊搜索。
3. `keyword` 做了 LIKE 转义：先替换反斜杠，再替换 `%` 和 `_`，并使用 `escape="\\"`。顺序不能反，否则会把新加的转义反斜杠再转一遍。
4. 返回 `to_admin_preview`，比前台多 `status` / `category_id` / `updated_at`。
5. 不返回 `content`，列表体积可控；预览时前端再单发一次详情请求。

## 新建 `Save`

流程与关键点：

1. **先查重**（`path` 已存在 → 直接 `Conflict`）。这只是快速路径，**不是并发保护**；两个请求同时通过查重后仍靠唯一索引兜底，所以 `except IntegrityError` 必须留着。
2. `category_name` 经 `CatService.GetOrSave(name, True)` 取 id。`GetOrSave` 内部会 commit 并 refresh，返回 `info(data={"id": ...})`。
3. 空串归一：`cover = data.cover or None`、`cover_public_id = data.cover_public_id or None`，避免库里同时存在 `""` 和 `NULL` 两种“没有封面”。
4. `commit()` 包在 `try/except IntegrityError` 里：回滚后按 MySQL errno 翻译成明确文案（见下）。
5. `refresh(article)` 后返回 `data={"id": ...}`，前端建完能跳到编辑页。

### `_conflict_detail`：把 MySQL 错误码翻成人话

| errno | 含义 | 返回文案 |
| :--- | :--- | :--- |
| 1062 | 唯一键冲突 | 该访问路径已被占用，请换一个 |
| 1048 / 1364 | NOT NULL 违例 / 无默认值 | 必填字段为空，请检查后重试 |
| 1406 / 1265 | 数据超长 / 超范围 | 字段内容过长，请精简后重试 |
| 其他 | 未识别 | 数据写入冲突，请检查必填项后重试 |

> `ArticleSaveRequest.path` 在 schema 里是 `Optional[str] = None`，但数据库列是 `NOT NULL`。不传 `path` 会在插入时触发 1048，最终以 409「必填字段为空」返回。前端必须传 `path`。

## 编辑 `Edit`：可空字段语义

这是全项目最容易改错的地方。`ArticleEditRequest` 的每个字段都按 **`data.model_fields_set`** 判断，不是真值判断：

- **键不出现** = 不改，保持原值；
- **键出现且为 `null` / 空串** = 清空。

```python
provided = data.model_fields_set

if data.title:            # NOT NULL 列：留空即不改，没有“清空”语义
    result.title = data.title
if "description" in provided:   # 可空列：键在就改
    result.description = data.description or None
```

具体分三类：

- **NOT NULL**（`title` / `path` / `content`）：只有真值才赋值。留空视为“不改”。
- **可空**（`description` / `cover` / `cover_public_id`）：键在就赋值，`null`/`""` 归一成 `None`。
- **`status`**：`is not None` 才改（语义与“键在就改”一致，也不会吞掉合法值）。
- **`category_name`**：真值才触发 `GetOrSave`。

`GetOrSave` 内部也会 commit（顺带把上面的脏字段一起刷库），所以 **`try/except IntegrityError` 必须把 `GetOrSave` 也包进来**——`path` 撞唯一索引的异常可能从那一行抛出，否则会穿成 500。

提交成功后，才做云端图片清理（见 `images.md`）：

1. 封面换过（含被清空）→ 旧封面可销毁，但先确认它没有被本文正文或其他文章引用；
2. 正文插图 → 对比新旧 HTML 的 `<img src>` 差集，把不再被引用的图反推 `public_id` 后销毁；
3. 图片若仍被当前封面或其他文章引用，跳过。

## 删除 `Remove`

顺序不能错：

1. **删除前**记录 `cover_public_id`、`cover` URL、正文里的 `<img src>`。commit 之后行已从库里消失，再读这些字段会触发异步懒加载并报错。
2. `db.delete(result)` + **显式 `await db.commit()`**。
3. commit 成功后才清理云端：封面（若无其他引用）与正文插图（若不再被引用）。
4. 清理是尽力而为：`destroy_image` 内部不抛异常，最多留一张孤儿图，不会让“删除成功”变失败。

反过来（先删图再提交）会出事：commit 失败回滚后文章还在、图已销毁，前台直接裂图且无法自愈。

## 栏目 `CatService`

```python
async def GetByName(name) -> Optional[int]   # 只读，未命中 None
async def GetOrSave(name, status)            # 查找；status=True 且不存在则创建
```

- `GetByName` 专供 GET 查询路径，**不写库**，且必须能区分“未命中”与“查到 id”。
- `GetOrSave` 返回 `info(data={"id": ...})`，内部 commit + refresh。
- **注意**：`GetOrSave(name, status=False)` 在未命中时会执行 `id = result.id`，`result` 是 `None` → `AttributeError`。当前调用方全部传 `True`；这是潜在雷，不要在未命中场景传 `False`。

## 相关 schema

| 模型 | 字段 |
| :--- | :--- |
| `ArticleSaveRequest` | `title`(必填) `path`(可选，但 DB NOT NULL) `description`(必填) `cover?` `cover_public_id?` `content` `status=1` `category_name`(必填) |
| `ArticleEditRequest` | 全部可选：`title` `path` `description` `cover` `cover_public_id` `content` `status` `category_name` |
| 返回 | `to_preview` / `to_detail` / `to_admin_preview` / `to_admin_detail`（见 `api.md` 与 `data-model.md`） |

两个请求模型都对 `content` 和 `cover` 挂了 `_reject_pending_images` 校验器：检测到 `data-pending-upload` 属性或 `blob:` 占位地址时直接 422，防止“漏 flush 的本地占位图”写进库。详见 `images.md`。