# 认证与用户（`services/auth.py` / `services/user.py` / `services/email.py`）

## 认证模型

- 密码用 **argon2**（passlib）哈希，绝不存明文。
- 令牌是 **JWT HS256，有效期 7 天**，载荷只有 `sub`（用户 id）、`username`、`jti`、`iat`、`exp`。
- **载荷里没有 `is_admin`**。权限每次请求由 `deps.GetCurrentUser` 回库取用户、`GetAdminUser` 再判，令牌被窃也无法凭陈旧声明提权。
- `jti` 是登出的前提：没有它就无法把某枚令牌单独拉黑。
- 令牌走**响应体** `access_token` 字段，不走 `Authorization` 响应头。跨源下自定义响应头默认对 JS 不可见，容易漏配 `Access-Control-Expose-Headers`。
- 解码时显式传 `algorithms=[ALGORITHM]`，不接受令牌自带的算法。

## `AuthService`

### `Login`

顺序很重要：

1. **IP + 账号双维度限流**（IP 60 次 / 账号 10 次 / 300 秒）。Redis 故障时放行并 `logger.error`。
2. **统一跑一次密码校验**：账号不存在时用 `DUMMY_PASSWORD_HASH` 跑等价开销的校验，抹平用户枚举的响应时间侧信道。
3. 校验失败统一回 `PwdError("邮箱或者密码错误")`，不区分“账号不存在”和“密码错”。
4. 账号状态不是 `1` → `OpError("账号已被禁用")`。
5. 签发令牌，返回 `{access_token, token_type:"bearer", id, email, username, avatar, bio, is_admin}`。

> **已知未修问题（CODE_REVIEW B-2）**：限流在密码校验**之前**执行，且账号维度只有 10 次/5 分钟。攻击者只要知道目标邮箱，就能反复提交错误密码把该账号的额度打满，导致真实用户 5 分钟内无法登录。当前未改为“只对失败计数”或“成功后重置”。改登录逻辑时要留意这个取舍。

### `Register`

1. 先校验并**一次性消费**邮箱验证码（`purpose="register"`）。
2. 查重（邮箱/用户名），冲突回 `OpError("邮箱或用户名已被注册")`。
3. `hash_password` 内部走 `run_in_threadpool`——argon2 很慢，不能阻塞事件循环。
4. **服务端写死 `is_admin=0`、`status=1`**，请求体里塞这两个字段会被 Pydantic 忽略。
5. 显式 `commit()`；`IntegrityError`（并发竞态）回滚后回 `OpError`，不抛 500。
6. 注册成功与登录同构，直接下发令牌，省一次往返。

### `Logout`

取 `jti` 写入 Redis 黑名单，TTL 取令牌剩余有效期。

- 黑名单查询失败时**失败开放**（放行 + 告警），避免 Redis 抖动导致所有请求 401。
- 但**写黑名单失败时失败关闭**：回“退出成功”等于骗用户，所以抛 `OpError("登出失败，请稍后重试")`。
- 返回体是 `info(data={"code":200, "msg":"退出成功"})`——`code`/`msg` 嵌在 `data` 里，属历史写法，前端不依赖它。

## 邮件验证码 `EmailService`

注册与注销共用一套逻辑，按 `purpose`（`register` / `delete`）隔离在各自的 Redis 命名空间：

| key | 作用 | TTL |
| :--- | :--- | :--- |
| `email:code:{purpose}:{email}` | 验证码本体 | 300 秒 |
| `email:code:attempts:{purpose}:{email}` | 错误次数 | 与验证码同 TTL |
| `email:code:cooldown:{purpose}:{email}` | 发送冷却 / 并发闸门 | 60 秒 |

`email` 只在拼 Redis key 时统一 `.strip().lower()`；落库与投递仍用用户原样输入。这样大小写不同的输入不会算出两套 key，也堵住“换大小写绕过 5 次/小时”的漏洞。

### 发送 `SendCode(email, request, purpose)`

- 有效期 **300 秒**，同一码最多错 **5 次**，重发冷却 **60 秒**。
- 发送限流：**邮箱 5 次/小时、IP 10 次/小时**。限流失败开放。
- 冷却键用 `SET NX` 抢占，既防连点，也防两个并发请求各自生成不同的码（后者会让先收到的那封邮件里的码失效）。
- **缓存命中时复用原码、不重新生成、不续期 TTL**；重发只重复投递同一封内容，避免前端倒计时被悄悄拉回 300 秒。
- 缓存未命中才生成新码：`secrets.randbelow(900000) + 100000`（6 位，密码学随机，不是 `random`）。
- **先发送成功、再写缓存**（S3）。反过来的话，Resend 失败会留下“缓存有码但用户没收到”的死状态。写缓存失败会释放冷却，让用户能立刻重试。
- Resend SDK 是**同步**实现，必须走 `run_in_threadpool`，否则卡住事件循环。
- 对外只返回 `{expires_in}`，**绝不在 HTTP 响应里回显验证码**；日志也只记用途与邮箱，不出现码明文；Resend 异常原文不外传。

### 校验 `VerifyCode(email, code, purpose)`

- 读缓存失败 → **失败关闭**，抛 `AppError`，绝不放行注册。
- 无码/过期 → `BadRequest("验证码已过期，请重新获取")`。
- 用 `secrets.compare_digest` 做恒定时间比较，避免按响应时间逐位猜码。
- 错误次数达 5 次 → 立刻删码，强制重新获取。
- 校验通过后用 Lua **原子消费**（`GET == 提交值` 才 `DEL`），压掉“先 GET 再 DEL”的并发重放窗口。
- 调用方**必须先确认要建号/删号再调用**：一旦成功，码就没了。

新增用途要同时补 `_PURPOSES` 和 `_MAIL_TEMPLATES`，否则会拼出没有模板的 key 或发不出邮件。

## `UserService`

身份只认路由层传入的 `User`（来自 `GetCurrentUser`），**service 不接受 user_id 参数**，也不从请求体取身份。这从结构上杜绝了 IDOR。

### `Edit`：只改用户名 / 头像 / 简介

- 入参 `UserEditRequest` 声明 `extra="forbid"`，邮箱、密码、`is_admin`、`status` 一律不可改。
- 可空字段（`avatar` / `bio`）沿用文章的 `model_fields_set` 语义：**缺键 = 不改，显式 `null` / 空串 = 清空**。空串会先 `strip()` 再归一成 `None`，不落空字符串。
- 用户名改了要先查重（`User.username == 新名 AND id != 当前 id`），冲突回 `Conflict("用户名已被占用")`；并发由唯一索引 + `IntegrityError` 兜底。
- 没有任何可改字段时直接返回当前资料，**不制造无意义的 UPDATE**。
- 返回 `to_user_profile`：`id` / `email` / `username` / `avatar` / `bio` / `is_admin`。
- 历史评论/留言展示的是发表时的昵称/头像快照，**不会随资料修改回写**。

### `AdminList`：只读用户列表

- 按 `User.id DESC` 分页（自增主键即注册顺序，且直接走 PK 索引；按 `created_at` 排会 filesort，该列无索引）。
- **列投影**，不加载 ORM 实体，从源头避免把 `password_hash` 带出去。
- `to_admin_user` 返回 `id` / `email` / `username` / `avatar` / `bio` / `is_admin` / `status` / `created_at`。
- service 侧再兜一层 `page >= 1`、`1 <= size <= 100`，防止绕过路由校验产生负 OFFSET。

### `RemoveSelf`：凭验证码注销自己

1. 验证码格式先卡（6 位数字），避免 `compare_digest` 拿到 `None`/超长串。
2. `EmailService().VerifyCode(user.email, code, purpose="delete")`。**注销码只能用于注销**，注册码不能拿来销号。
3. 若当前用户是管理员：`SELECT ... WHERE is_admin=1 AND status=1 FOR UPDATE`，若可用管理员只剩自己 → `Conflict("不能注销唯一的管理员账号...")`。`FOR UPDATE` 堵住“两个管理员同时自删、各自看到对方还在”的竞态。
4. `db.delete(user)` + 显式 `commit()`；`IntegrityError` 回滚后回 `Conflict`，不抛 500。
5. 评论/留言的 `user_id` 是 `ON DELETE SET NULL`，正文与昵称快照保留。
6. **不额外拉黑当前令牌**：下一请求 `GetCurrentUser` 查不到用户自然 401，与“用户已删除”的既有处理一致。

> 异常路径里只能使用提前取好的局部 `user_id`。`rollback()` 会 expire 持久化实例，之后再读 `user.id` 会触发同步懒加载，在 `AsyncSession` 下变成 `MissingGreenlet`。

## 前端令牌存储

两个前端各存各的，互不共享：

| 应用 | 存储 | 键 |
| :--- | :--- | :--- |
| `web/` | `useState` + localStorage | `fishmo_access_token` / `fishmo_user` |
| `admin/` | Pinia + localStorage | `blog_admin_token` / `blog_admin_user` |

两者都走 `Authorization: Bearer`。`GetCurrentUser` 对“令牌无效 / 用户已删 / `status != 1`”一律回 401，前端统一按重新登录处理。