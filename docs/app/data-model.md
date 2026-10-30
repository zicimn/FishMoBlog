# 数据模型、常量与索引

## 表一览

| 表 | 模型 | 用途 |
| :--- | :--- | :--- |
| `article` | `models/article.py` | 文章 |
| `category` | `models/category.py` | 栏目 |
| `comment` | `models/comment.py` | 评论（一层回复树） |
| `msg` | `models/msg.py` | 留言板（一人一条） |
| `user` | `models/user.py` | 用户 / 管理员 |

模型统一继承 `config.db.Base`，字段用 SQLAlchemy 2.0 的 `Mapped[...] / mapped_column(...)`。

## `article`

| 列 | 类型 | 可空 | 说明 |
| :--- | :--- | :--- | :--- |
| `id` | int PK 自增 | 否 | |
| `path` | varchar(255) | 否 | slug，**唯一索引** `uk_article_path` |
| `title` | varchar(255) | 否 | |
| `description` | varchar(500) | 是 | 摘要 |
| `cover` | varchar(500) | 是 | 封面 URL |
| `cover_public_id` | varchar(255) | 是 | 封面在云端的清理凭据 |
| `content` | text | 否 | 正文 HTML（**未消毒**） |
| `style` | varchar(50) | 是 | 文章页自定义背景色（CSS 颜色值），不是样式表 |
| `category_id` | int FK → `category.id` | 是 | `ON DELETE SET NULL` |
| `status` | int / tinyint | 否 | 默认 1；代码语义 `1 正常 / 2 隐藏 / 3 草稿` |
| `views` | int | 否 | 默认 0；真实值 = 库内值 + Redis 未回写增量 |
| `created_at` | datetime | 否 | Python 侧 `datetime.now`，SQL 侧 `CURRENT_TIMESTAMP` |
| `updated_at` | datetime | 否 | `onupdate=datetime.now` |

关系：`category` 用 `lazy="selectin"`、`passive_deletes=True`。详情查询会 `noload(Article.category)` 避免多打一条查询，同时避免异步下访问 `article.category.name` 触发懒加载报错。

索引：

- `uk_article_path(path)` —— 唯一，路由按 slug 查。
- `idx_article_category(category_id)` —— 前台按栏目筛。
- `idx_article_status(status)` —— 前台可见性过滤。
- `idx_article_created(created_at)` —— 列表按时间倒序。

> **DDL 注释过期**：`app/sql/*.sql` 里 `article.status` 的注释还是「0不可视 1可视」，与代码的 `1/2/3` 不符。以模型与 `STATUS_*` 常量为准。

### 状态常量

```python
STATUS_NORMAL = 1   # 正常，对外可见
STATUS_HIDDEN = 2   # 隐藏，仅后台可见
STATUS_DRAFT  = 3   # 草稿，仅后台可见
STATUS_PUBLIC = (STATUS_NORMAL,)   # 前台可见集合
```

前台列表/详情/评论解析都用 `status.in_(STATUS_PUBLIC)`；后台列表不筛状态。

## `category`

| 列 | 类型 | 可空 | 说明 |
| :--- | :--- | :--- | :--- |
| `id` | int PK | 否 | |
| `name` | varchar(50) | 否 | **唯一索引** `uk_category_name` |
| `created_at` / `updated_at` | datetime | 否 | |

没有独立的栏目管理接口。栏目在文章保存时通过 `CatService.GetOrSave(name, True)` **按名字自动创建**；读接口只用 `GetByName`，不写库。

## `comment`

| 列 | 类型 | 可空 | 说明 |
| :--- | :--- | :--- | :--- |
| `id` | int PK | 否 | |
| `article_id` | int FK → `article.id` | 否 | `ON DELETE CASCADE` |
| `parent_id` | int FK → `comment.id` | 是 | `ON DELETE CASCADE`；NULL = 顶层 |
| `user_id` | int FK → `user.id` | 是 | `ON DELETE SET NULL`；NULL = 访客/历史/已注销 |
| `user_name` | varchar(50) | 否（模型） | 昵称快照 |
| `user_email` | varchar(100) | 是 | **历史遗留列，代码从不写入、也不返回** |
| `user_avatar` | varchar(500) | 是 | 头像快照 |
| `content` | text | 否 | 消毒后的 HTML |
| `content_text` | text | 是 | 去标签纯文本，截断 500 字，用于后台预览/查重 |
| `status` | int | 否 | 默认 1；`0 待审核 / 1 正常 / 2 屏蔽` |
| `created_at` | datetime | 否 | |

索引：`idx_comment_article` / `idx_comment_parent` / `idx_comment_user` / `idx_comment_status`。查询模式是“按文章 + 顶层 + 状态 + 时间倒序”，以及“按父 id 批量取回复”。

### 评论状态常量

```python
COMMENT_STATUS_PENDING = 0
COMMENT_STATUS_NORMAL  = 1
COMMENT_STATUS_HIDDEN  = 2
```

从 `models` 导出时加了 `COMMENT_` 前缀，因为评论模型文件里的常量名与文章模型**重名**（都叫 `STATUS_NORMAL` 等）。不要混用两套值。

## `msg`

| 列 | 类型 | 可空 | 说明 |
| :--- | :--- | :--- | :--- |
| `id` | int PK | 否 | |
| `user_id` | int FK → `user.id` | 是 | `ON DELETE SET NULL`；**唯一索引 `uk_msg_user`** |
| `username` | varchar(50) | 否 | 昵称快照 |
| `avatar` | varchar(500) | 是 | 头像快照 |
| `content` | text | 否 | 消毒后的 HTML |
| `ip` | varchar(255) | 否 | 仅审计，**永不对外返回** |
| `created_at` | datetime | 否 | |

`uk_msg_user` 保证“一人一条”。MySQL 唯一索引允许多个 NULL，所以删号后的历史留言可以并存。该索引需要按 `app/sql/msg.sql` 手工执行；已经有表但没有唯一约束的环境，补跑文件末尾的 `ALTER TABLE`。

## `user`

| 列 | 类型 | 可空 | 说明 |
| :--- | :--- | :--- | :--- |
| `id` | int PK | 否 | |
| `username` | varchar(50) | 否 | 唯一索引 `ix_user_username` |
| `email` | varchar(100) | 否 | 唯一索引 `ix_user_email` |
| `password_hash` | varchar(255) | 否 | argon2，**任何接口都不返回** |
| `avatar` | varchar(255) | 是 | |
| `bio` | text | 是 | |
| `status` | smallint | 是 | 默认 1；`0 禁用 / 1 正常` |
| `is_admin` | smallint | 是 | 默认 0；`0 访客 / 1 管理员` |
| `created_at` / `updated_at` | datetime | 否 | |

用户状态是 `0/1`，与文章 `1/2/3`、评论 `0/1/2` 都不同。`GetCurrentUser` 只放行 `status == 1`。

管理端用户列表按 `id DESC` 分页（PK 索引，等价于注册顺序倒序），用列投影避免带出 `password_hash`。

## 可空字段的“不改 vs 清空”语义

文章编辑（`ArticleEditRequest`）与用户资料编辑（`UserEditRequest`）都按 **`data.model_fields_set`** 判断，不是真值判断：

| 请求体 | 行为 |
| :--- | :--- |
| 键不出现 | 保持原值 |
| 键出现，值为 `null` 或 `""` | 清空（落库为 `NULL`） |
| 键出现，值为新内容 | 更新 |

前端对应做法：对可空字段“发键 + null 或新值”，而不是省略键。改回 `if data.xxx:` 会让“清空封面/摘要/头像/简介”永久失效——这是本轮明确修掉的老问题。

NOT NULL 字段（`title` / `path` / `content`）没有“清空”语义，传空值时视为不改。

## 外键删除行为

| 外键 | 行为 | 后果 |
| :--- | :--- | :--- |
| `comment.article_id` | `ON DELETE CASCADE` | 删文章连带删评论 |
| `comment.parent_id` | `ON DELETE CASCADE` | 删父评论连带删子孙（应用层还会先 BFS 倒序删） |
| `comment.user_id` | `ON DELETE SET NULL` | 注销账号保留评论正文与昵称快照 |
| `msg.user_id` | `ON DELETE SET NULL` | 注销账号保留留言正文与昵称快照 |
| `article.category_id` | `ON DELETE SET NULL` | 删栏目不影响文章（当前没有栏目删除接口） |

## 没有自动建表 / 没有迁移

全仓**没有** `create_all`，**没有** Alembic。改模型不会同步数据库，表结构变更必须手工 SQL：

- `app/sql/build.sql` —— 一次性建全部表的脚本（会 `DROP TABLE`，**只在空库/初始化时用**）。
- `app/sql/blog.sql` —— Navicat 导出的完整结构 + 示例数据。
- `app/sql/msg.sql` —— 留言表与唯一索引的增量脚本。

这些文件都在 `.gitignore` 里，不分发。**注意 `blog.sql` / `build.sql` 的示例数据里可能含真实账号哈希、邮箱、Cloudinary 云名与图片 URL**；只把它们当本机迁移工具，不要提交、不要外传。

典型变更（例如新增 `article.cover_public_id`）需要在目标库手工执行：

```sql
ALTER TABLE article
  ADD COLUMN cover_public_id VARCHAR(255) NULL COMMENT '封面在云存储的 public_id'
  AFTER cover;
```

## 时间字段

Python 侧默认值用 `datetime.now`（**naive 本地时间**），SQL 侧是 `CURRENT_TIMESTAMP`。项目没有统一时区处理，JSON 序列化出来是不带时区的 ISO 字符串，前端按本地时间展示。跨时区部署时要留意这一点。

## Redis 里的数据

MySQL 之外，Redis 存四类数据（都在 `config/cache.py` / 各 service 里）：

| key 模式 | 用途 | TTL |
| :--- | :--- | :--- |
| `rl:<业务 key>` | 固定窗口限流计数 | 窗口长度 |
| `jwt:blacklist:<jti>` | 登出令牌黑名单 | 令牌剩余有效期 |
| `article_views`（hash） | 浏览量增量，每 300 秒回写 MySQL | 无（回写后 HDEL） |
| `email:code:{purpose}:{email}` 等 | 邮箱验证码 / 错误次数 / 冷却 | 300 / 同码 / 60 秒 |

`config/cache.py` 里还定义了 `get_cache_key` / `get_from_cache` / `set_to_cache` / `delete_cache` / `delete_cache_pattern`（`SCAN` 而非 `KEYS`，反序列化用 `json.loads`）等通用缓存工具，**但当前没有任何 service 调用它们**——项目目前没有接口级响应缓存。不要误以为某个接口“有缓存”；改性能前先看代码。

## 历史残留

- 专栏功能相关代码与模型已删（`models/column.py`、`models/associations.py`、旧 `api/comment.py` 单数参考文件均不存在），但**数据库里可能还留着那几张表**，需要手工 `DROP`。
- `comment.user_email` 列仍在表里，但代码从不写入、从不返回。不要因为看到列就以为评论会收集邮箱。
- `utils/verify.py` 的 `verify_login` 与 `schemas/user.py` 的 `ResetPwdRequest` 都没有调用方，属死代码。