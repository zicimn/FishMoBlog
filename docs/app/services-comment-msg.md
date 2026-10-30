# 评论与留言（`services/comment.py` / `services/msg.py`）

评论挂在文章下，支持一层回复；留言板是全局的，一人一条。两者都要求登录，作者身份与 IP **只从服务端取**，请求体不接受 `user_id` / `ip`。

## 评论 `ComService`

### 状态常量

评论侧定义在 `models/comment.py`，从 `models` 导出时加了 `COMMENT_` 前缀（避免与文章的同名常量冲突）：

| 常量 | 值 | 含义 |
| :--- | :--- | :--- |
| `COMMENT_STATUS_PENDING` | 0 | 待审核 |
| `COMMENT_STATUS_NORMAL` | 1 | 正常（前台可见） |
| `COMMENT_STATUS_HIDDEN` | 2 | 已屏蔽 |

文章的状态是 `1/2/3`，**两套值不通用**。

### `GetList(path, page, size)`：前台评论树

1. **只读解析文章**：`_resolve_article(path)` 先按 `Article.path` 精确匹配，查不到再把 `path` 当数字 id 查，两步都要求 `status in STATUS_PUBLIC`。顺序固定，避免数字型 slug 与 id 撞车。
2. **不要复用 `ArticleService.GetSlug`**：后者会自增浏览量，打开一次评论列表就会把文章浏览量刷高一次。这里用 service 自己的只读解析。
3. 根评论：`article_id = ? AND parent_id IS NULL AND status = 1`，按 `created_at DESC, id DESC` 分页。
4. 回复：只查 `parent_id IN (当前页根评论 id) AND status = 1`，按时间正序。
5. `replies_by_parent` 的 key 必须是 **int** 父 id。历史上写入用 int、读取用 `str(root.id)`，导致 `child` 恒为空——不要再改成字符串 key。
6. 返回 `info(data=[...])`，**没有 `total`**（评论列表不分页总数给前端，靠 `hasMore` 推断）。

### `GetTop(limit)`：侧边栏最新评论

一次 `JOIN Article` 取回评论 + 文章 `path/title`，避免逐条再查文章（N+1）。只取正常评论，按时间倒序，默认 5 条、上限 20。返回 `to_top_item`，比普通条目多 `articleId` / `articlePath` / `articleTitle`——没有它们前端拼不出跳转链接（前台路由走 slug）。

### `AdminList(page, size, status)`

- 不按文章过滤、不带回复树、**不限制 status**（后台必须能看见待审核与已屏蔽）。
- 一次 `JOIN Article` 带出文章 `path/title`，扁平分页，按时间倒序。
- 返回 `{total, items}`，条目是 `to_admin_comment`。
- **刻意不返回 `user_email`**：邮箱是非公开字段，管理列表也用不上。

### `Create(article_ref, data, user, client_ip)`

1. **限流**：IP 10 次/60 秒 + 用户 5 次/60 秒；Redis 故障失败开放并告警。
2. 解析文章（slug 优先，数字 id 兜底，只认可见文章）。
3. 若带 `parent_id`：父评论必须存在、属于同一篇文章、且 `status=1`，否则 `NotFound("被回复的评论不存在")`。父评论被屏蔽时对外等同于不存在，不泄露其状态。
4. **先 `sanitize_html` 再落库**：`content` 存清洗后的 HTML；`content_text` 由清洗后的结果去标签、截断 500 字派生，用于后台预览/查重。
5. 清洗后为空（例如只提交了 `<script>`）→ `OpError("评论内容不能为空")`。AppError 体系没有 400，这里借 `OpError`（403，“这次操作不被接受”）；原始空白/长度仍由 Pydantic 在 422 层拦掉。
6. 写快照：`user_name` / `user_avatar` 取自当前用户，用户日后改名/换头像不影响历史评论。**刻意不写 `user_email`**（评论表是半公开数据，邮箱不外泄）。
7. 显式 `commit()`，返回 `to_comment_result`。

> 请求体字段：`content`（1–2000）、`article`（Pydantic 别名，接受 `article_id` / `articleId` / `path`）、`parent_id`（接受 `parent_id` / `parentId`）。多传未声明字段会被忽略或拒绝。

### `Remove(comment_id, user)`

1. 只有作者本人或管理员可删；`user_id` 为 NULL 的历史/访客评论只有管理员能删。
2. **BFS 逐层收集所有后代**（不依赖 MySQL 递归 CTE，保证版本兼容）。
3. **由深到浅**逐个 `db.delete()`：先子孙后自身，避免与 `parent_id` 的 `ON DELETE CASCADE` 抢同一批行。
4. 必须用 ORM 对象逐个删，不能用 bulk delete——bulk 不走 ORM 状态跟踪，依赖 `get_db` 兜底提交不可靠。
5. 显式 `commit()`。

> **已知限制（CODE_REVIEW M-4）**：`Create` 允许回复任何一条正常评论（包括回复的回复），但 `GetList` 只取“父级是顶层评论”的一层回复。因此**回复一条回复能入库，但永远不会显示**。前端 UI 也因此不提供该入口。要支持多层回复，需要同时改 `GetList` 的查询与前端渲染。

### 消毒规则

`utils/sanitize.py` 用 nh3，**显式白名单**：

- 允许的标签不含 `img`；
- 属性只允许 `a` 的 `href` / `title`；
- 链接协议只允许 `http` / `https` / `mailto`；
- 统一加 `rel="noopener noreferrer"`；
- 去掉注释。

评论与留言共用这一套。前端渲染用 `v-html`，安全性依赖后端消毒；**不要把原始输入直接当 HTML 提交**（web 侧先用 `utils/comment.ts` 转义再把换行转 `<br>`）。

## 留言板 `MsgService`

### 数据形态

- `msg` 表：`user_id`（`ON DELETE SET NULL`）、`username` / `avatar` 快照、`content`（消毒后的 HTML）、`ip`（仅审计）、`created_at`。
- `uk_msg_user` 唯一索引保证**一个账号只能有一条留言**；应用层先查一次给出友好提示，索引负责并发兜底。该索引需按 `app/sql/msg.sql` 手工执行（项目无自动建表/迁移）。
- 删掉自己的留言后可以重新发。

### `MCreate(data, user, client_ip)`

1. 先查“是否已留过言”，已存在 → `Conflict("你已经创建过了")`。
2. IP 10 次/60 秒 + 用户 5 次/60 秒限流，失败开放。
3. `sanitize_html` 清洗；清洗后为空 → `OpError("留言内容不能为空")`。
4. 写入 `user_id` / `username` / `avatar` 快照与 `ip`（IP 来自 `request.client.host`，请求体不接受）。
5. `commit()`；`IntegrityError`（并发重复）回滚后同样回 `Conflict`。

请求体模型 `MsgCreateRequest` 是 `extra="forbid"`，只接受 `content`（1–2000）；多传 `user_id` / `ip` 等字段直接 422。

### `MGetList(page, size)`

按 `created_at DESC, id DESC` 分页，返回 `{total, items}`。`to_mdetail` **刻意不返回 `ip`**：公开列表匿名可读，把 IP 带出去等于把留言者网络地址交给任何爬虫。返回字段：`id` / `user_id` / `content` / `username` / `avatar` / `created_at`。

### `MRemove(msg_id, user)`

本人或管理员可删。`user_id` 为 NULL（账号已注销）的留言**仅管理员可删**。硬删 + 显式 `commit()`。

## 前端对应关系

- 前台文章页评论区：`GET /comments/{path}`（分页参数 `p`）、`POST /comments`、`DELETE /comments/{id}`。发表根评论后回第 1 页（新评论倒序），回复成功原地 `refresh()`。
- 前台留言板：`GET /msg/list`（分页参数 `p`）、`POST /msg`、`DELETE /msg/del?id=`。能否删除由 `user.id` 判断（`to_user_info` 因此返回 `id`）。
- 管理端：`GET /admin/comment/list` 与 `GET /msg/list`，列表内容都是后端消毒过的 HTML，用 `v-html` 渲染，删除走确认弹窗。