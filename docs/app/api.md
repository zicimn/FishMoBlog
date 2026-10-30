# 接口清单

所有接口都在 `main.py` 的 `service_router` 下注册，共 **26 条业务路由**（加上 FastAPI 自带的 `openapi` / `docs` / `oauth2-redirect` / `redoc` 共 30 条）。核对方式：

```bash
cd app && ../.venv/Scripts/python.exe -c "import main; print(len(main.app.routes))"   # 30
```

## 通用约定

### 响应信封

除个别例外，返回体是 `utils/responsed.py` 的 `info()` 拼的裸 dict：

```json
{ "msg": "成功", "code": 200, "data": null }
```

`code` 是业务码（默认 200），`msg` 是中文提示，`data` 是载荷。**没有 `response_model`**，字段契约靠 `schemas/*.py` 的 `to_xxx()` 函数和前端 `types/` 手工对齐。

### 错误状态码

Service 层抛 `AppError` 子类，路由层转 `HTTPException`：

| 异常类 | HTTP 状态 | 语义 |
| :--- | :--- | :--- |
| `AppError` | 500 | 未分类服务端错误 |
| `BadRequest` | 400 | 参数/业务前置条件不满足 |
| `NotFound` | 404 | 资源不存在 |
| `PwdError` | 401 | 邮箱或密码错误 |
| `OpError` | 403 | 无权限 / 账号被禁用 / 操作不允许 |
| `Conflict` | 409 | 唯一索引冲突 |
| `Busy` | 429 | 触发限流 |

`Conflict` 是专为唯一索引冲突新增的，**不要用 `OpError` 顶替**——前端会把 `OpError` 翻成“需要管理员权限”。

### 鉴权

- 令牌放在请求头 `Authorization: Bearer <token>`。
- 令牌本身从登录/注册**响应体的 `access_token` 字段**返回，不走响应头。
- JWT 载荷只有 `sub` / `username` / `jti` / `iat` / `exp`，**没有 `is_admin`**；每次请求由 `deps.GetCurrentUser` 回库取用户，`GetAdminUser` 再判管理员。
- 管理端所有接口由 `api/admin.py` 的 **router 级** `dependencies=[Depends(GetAdminUser)]` 统一拦截，新增端点自动继承，不要逐个加。

### 422 的 `detail` 是数组

Pydantic 校验失败时 FastAPI 返回 `{"detail": [{"loc": [...], "msg": "...", ...}]}`，且内置文案是英文。两个前端的处理不同：

- `admin` 的 `useApi.ts` 把各条 `msg` 拼起来；
- `web` 的 `utils/api.ts` 只采纳含中文的条目，否则按状态码兜底中文。

不要假设 422 一定有中文。

## 公开接口（无需登录）

| 方法 | 路径 | 参数 | 返回 `data` |
| :--- | :--- | :--- | :--- |
| GET | `/article/` | `page`(≥1, 默认1) `size`(1–50, 默认16) `category_name`(≤200) | `{total, items:[ArticlePreview]}` |
| GET | `/article/{path}` | 路径参数 `path` | `ArticleDetail`；**会自增浏览量** |
| GET | `/comments/top` | `limit`(1–20, 默认5) | `[TopCommentItem]` |
| GET | `/comments/{path}` | `p`(≥1, 默认1) `size`(1–50, 默认10) | `[CommentItem]`（一层回复树） |
| GET | `/msg/list` | `p`(≥1, 默认1) `size`(1–50, 默认10) | `{total, items:[MsgItem]}` |
| POST | `/auth/email-code` | body `{email}` | `{expires_in}`（默认 300 秒） |
| POST | `/auth/register` | body `RegisterRequest` | `{access_token, token_type, id, email, username, avatar, bio, is_admin}` |
| POST | `/auth/login` | body `{email, password}` | 同上 |

注意：

- **分页参数不统一**：文章用 `page`，评论与留言用 `p`。前端分别对应。
- `/article/` 带尾斜杠；`/article` 会被 Starlette 重定向。前端请求的是 `/article/`。
- 公开详情只走 `/{path}`（slug），没有公开的按数字 id 取文章。
- `/comments/{path}` 的 `path` 是文章 slug；评论按根评论倒序分页，回复只返回**直接子级**（见 `services-comment-msg.md` 的已知限制）。

## 登录用户接口

| 方法 | 路径 | 参数 | 返回 `data` |
| :--- | :--- | :--- | :--- |
| POST | `/comments` | body `CommentCreateRequest` | `CommentResult` |
| POST | `/comments/{path}` | body `{content, parent_id?}` | 同上（**已 deprecated**，前端统一走 `/comments`） |
| DELETE | `/comments/{comment_id}` | 路径参数 | 无（`msg` 提示） |
| POST | `/msg` | body `{content}` | `MsgItem` |
| DELETE | `/msg/del` | query `id`(≥1) | 无（`msg` 提示） |
| PUT | `/user/profile` | body `UserEditRequest` | `UserProfile`（id/email/username/avatar/bio/is_admin） |
| POST | `/user/delete-code` | 无 body | `{expires_in}` |
| DELETE | `/user/self` | body `{code}` | 无（`msg` 提示） |
| POST | `/auth/logout` | 需有效令牌 | `{code:200, msg:"退出成功"}`（嵌在 `data` 里，历史写法） |

身份一律取自 `GetCurrentUser`，**请求体里没有 `user_id`**：

- 评论/留言的作者快照、IP 由服务端从登录态和 `request.client.host` 取；请求体多传 `user_id` / `ip` 会 422（`extra="forbid"` 或模型未声明字段）。
- 删除评论：作者本人或管理员；删除时会**级联删子孙**（BFS 收集后倒序删）。
- 删除留言：本人或管理员；账号已删除（`user_id` 为 NULL）的留言**仅管理员可删**。
- 注销账号：验证码通过后硬删 user；`user_id` 外键是 `ON DELETE SET NULL`，历史评论/留言正文与昵称快照保留；**唯一可用管理员不能自删**。

## 管理端接口（全部需要 `is_admin`）

前缀 `/admin`，router 级守卫。共 9 条：

| 方法 | 路径 | 参数 | 返回 |
| :--- | :--- | :--- | :--- |
| POST | `/admin/article/save` | body `ArticleSaveRequest` | `data={id}` |
| PUT | `/admin/article/edit/{id}` | body `ArticleEditRequest` | 无（`msg`） |
| DELETE | `/admin/article/remove/{id}` | 路径参数 | 无（`msg`） |
| GET | `/admin/article/list` | `page`(≥1,默认1) `size`(1–100,默认20) `status`(1–3) `keyword`(≤100) `category_name`(≤200) | `{total, items:[AdminArticlePreview]}` |
| GET | `/admin/article/{id}` | 路径参数 | **裸 `AdminArticleDetail`，无信封** |
| GET | `/admin/comment/list` | `page`(≥1,默认1) `size`(1–100,默认20) `status`(0–2) | `{total, items:[AdminComment]}`（扁平，含回复） |
| GET | `/admin/user/list` | `page`(≥1,默认1) `size`(1–100,默认20) | `{total, items:[AdminUser]}`（只读，不含 `password_hash`） |
| POST | `/admin/upload/image` | body `{image: <base64 字符串>}` | `{url, public_id}` |
| DELETE | `/admin/upload/image` | query `public_id`(1–255) | 无（`msg`） |

两个必须记住的点：

1. **`GET /admin/article/{id}` 是唯一不走信封的接口**。`ArticleService.GetId(id, status=True)` 直接返回 `to_admin_detail(...)` 裸 dict。管理端 `useApi` 用“有 `data` 和 `code` 才拆信封”来兼容它。
2. **图片删除的 `public_id` 走 query 参数**，因为 `public_id` 形如 `fishmo_upload/abc` **含斜杠**，放进路径参数会被路由拆开。上传/删除都只允许 `fishmo_upload/` 前缀，见 `images.md`。

### 后台与前台的状态值不同

- 文章 `status`：`1` 正常 / `2` 隐藏 / `3` 草稿。前台列表只查 `STATUS_PUBLIC=(1,)`；后台列表不筛可见性（否则管理端看不到隐藏与草稿）。
- 评论 `status`：`0` 待审核 / `1` 正常 / `2` 屏蔽。前台列表只看正常，后台可按 0/1/2 筛。
- 用户 `status`：`0` 禁用 / `1` 正常（不是 1/2/3）。

## 限流参数

Redis 固定窗口（Lua `INCR` + 仅首次 `EXPIRE`），失败时**放行**并打 `logger.error`：

| 场景 | 维度与上限 | 窗口 |
| :--- | :--- | :--- |
| 登录 | IP 60 次、账号 10 次 | 300 秒 |
| 注册 | IP 5 次 | 3600 秒 |
| 发验证码 | 邮箱 5 次、IP 10 次；另有 60 秒冷却 | 3600 秒 |
| 发评论 | IP 10 次、用户 5 次 | 60 秒 |
| 发留言 | IP 10 次、用户 5 次 | 60 秒 |

**登录限流在密码校验之前执行**，因此“账号维度 10 次/5 分钟”可被用来定向锁住某个已知邮箱（CODE_REVIEW B-2，当前仍未修）。这是已知取舍，改动登录逻辑时要心里有数。

## 路由顺序约束

`api/article.py` 里 `/{path}` 是动态兜底，**必须注册在最后**。Starlette 按注册顺序匹配，它排前面会把具体路径全吃掉。

同类情况：`/comments/top` 必须排在 `/comments/{path}` 之前；`/admin/article/list` 必须排在 `/admin/article/{id}` 之前。

`tests/test_smoke.py` 里本来有用例锁这两个约束，但它断言的是**复数路由**（`/articles/`、`/articles/id/{id}`），与当前单数代码不符，处于失败状态，**不要把它当有效护栏**。改完路由自己看一眼 `main.app.routes` 的顺序。

## 已废弃但保留的路由

`POST /comments/{path}` 仍注册着，但已 deprecated。前端统一走 `POST /comments`（文章标识放 body 的 `path`）。确认没有旧调用方后可以删。