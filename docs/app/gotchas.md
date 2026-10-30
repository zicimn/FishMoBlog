# 后端踩坑清单

按“会直接导致数据错误 / 线上事故”的优先级排列。每条都给出“为什么”和“怎么验证”。

## 1. 包根是 `app/`，不是仓库根

`app/` 下的模块都是顶层包。`from config import ...` 能跑，`from app.config import ...` 不能；`from ..deps import ...` 会报：

```text
ImportError: attempted relative import beyond top-level package
```

- 所有命令先 `cd app`，或把 `app/` 加进 `sys.path`（`tests/conftest.py` 的做法）。
- 跨层只用绝对导入。
- 验证：

```bash
cd app && ../.venv/Scripts/python.exe -c "import main; print(len(main.app.routes))"
# 30
```

## 2. 写操作必须显式 `await db.commit()`，不能只 `flush()`

`config/db.py` 的 `get_db` 只在 `session.new` / `dirty` / `deleted` 非空时提交。`flush()` 会把这几个集合清空，于是请求结束时 `get_db` 认为“没有变更”而不提交，写入被**静默回滚**，接口却返回成功。

所以 `Remove` / `Edit` / `Create` / `Register` / `Edit`（用户资料）/ `RemoveSelf` / `MCreate` 等方法都显式 commit。新增写方法时照做。

验证思路：真跑一遍请求再回库查，不要只看函数返回值。

## 3. Service 方法用 PascalCase

`GetId` / `GetSlug` / `AdminList` / `Save` / `Edit` / `Remove` / `GetOrSave` / `Upload` / `MCreate`……这是既有风格。改成 snake_case 会牵动所有调用方，不要“顺手规范化”。

## 4. 路由顺序：动态兜底必须最后注册

Starlette 按注册顺序匹配：

- `api/article.py`：`GET /{path}` 必须在 `GET /` 之后，且是最后一条。
- `api/comments.py`：`GET /top` 必须在 `GET /{path}` 之前。
- `api/admin.py`：`GET /article/list` 必须在 `GET /article/{id}` 之前。

排错时直接打印顺序：

```bash
cd app && ../.venv/Scripts/python.exe -c "
import main
for r in main.app.routes: print(sorted(r.methods or []), r.path)
"
```

`tests/test_smoke.py` 里锁路由顺序的用例断言的是**复数路由**（`/articles/`、`/articles/id/{id}`），与当前单数代码不符，处于失败状态，**不是有效护栏**。

## 5. `GetId` 与 `GetSlug`：谁自增浏览量

- `GetSlug(path)`：前台详情，**会** `ArticleViewCounter.incr`，并用 `get_total` 把 Redis 增量算进返回值。
- `GetId(id, status=...)`：按数字 id 查，**不会**自增；`status=True` 只是放开可见性过滤（后台语义）。

任何新接口都不要为了“读一篇文章”去复用 `GetSlug`，否则会刷高浏览量。评论列表就是因为复用过它，后来改成了 `ComService` 自己的只读解析。

> 文档/CLAUDE.md 里有一处写成“`ArticleService.GetId` 会顺带 incr”，与代码不符；**以 `GetSlug` 为准**。

`get_total` 是 `async`，漏 `await` 会把 coroutine 塞进响应体，序列化直接 500。

## 6. 浏览量回写：先读 → 写库成功 → 再 HDEL

`utils/counter.py` 的 `sync_to_db` 顺序不能反。原实现把 `hgetall + delete` 放进一个 pipeline，Redis 增量在 UPDATE 之前就被清空，一失败就永久丢失。

SQL 侧的三个坑（代码注释里都有）：

1. **必须有 `WHERE`**：`update(Article.__table__).where(...)`。曾经漏 WHERE，一次回写把所有文章浏览量写成同一个值（CODE_REVIEW B-3，已修）。
2. **`bindparam` 名不能与列名相同**：用 `b_id` / `b_delta`，否则 SQLAlchemy 会把参数和列混淆。
3. **用 Core `Article.__table__`，不要传 ORM 实体**：给 ORM 实体传 list 会被改写成“按主键批量更新”，行为与预期不符。

`SYNC_INTERVAL_SECONDS = 300`，后台任务由 `main.py` lifespan 启停。

## 7. Redis 降级策略是“故意不一致”的

| 场景 | 策略 | 原因 |
| :--- | :--- | :--- |
| 限流 | 失败**开放**（放行 + 告警） | Redis 抖动不该让所有人无法登录/评论 |
| 黑名单查询 | 失败**开放**（放行） | 否则所有请求 401 |
| 登出写黑名单 | 失败**关闭**（抛 `OpError`） | 回“退出成功”等于骗用户 |
| 验证码读写 | 失败**关闭**（抛 `AppError`） | 缓存挂了就无法验证，绝不能放行注册 |
| 浏览量 incr/get | 失败降级（不涨，不 500） | 详情页不能因 Redis 挂掉而崩 |

改这些地方时保持取向，不要“统一成一种”。

## 8. 登录限流可被用来定向锁账号（B-2，未修）

`AuthService.Login` 在**密码校验之前**执行 IP + 账号双维度限流（账号 10 次/5 分钟）。知道目标邮箱的人可以反复提交错误密码打满额度，让真实用户 5 分钟内无法登录。

这是已知未修问题。若要让限流只对失败计数，需要把限流拆成“预检 + 失败后计数/成功后重置”，并注意别引入新的用户枚举侧信道。

## 9. 回复一条回复能入库，但永远不显示（M-4，未修）

`ComService.Create` 允许 `parent_id` 指向任何同文章、正常状态的评论（包括回复）。但 `GetList` 只查“父级是顶层评论”的一层回复。结果：回复的回复入库了，前台永远看不到。

前端 UI 因此不提供该入口。要支持多层回复，必须同时改 `GetList` 的查询与前端渲染。

## 10. 422 的 `detail` 是数组

Pydantic 校验失败时 `detail` 是 `[{loc, msg, ...}]`，不是字符串。前端：

- `admin` 拼接各条 `msg`；
- `web` 只采纳含中文的条目，否则按状态码兜底中文。

不要假设后端一定给中文，也不要在前端把 `detail` 当字符串直接展示。

## 11. 文章正文未消毒；评论白名单不含 `img`

`sanitize_html`（nh3）只用于评论与留言，白名单**刻意不含 `img`**（允许的标签里没有图片，属性只允许 `a[href,target]` 之类）。文章正文存的是管理员写的原始 HTML，前端 `v-html` 直接渲染。

目前只有管理员能写文章，风险有限。若日后要消毒正文，必须按 `utils/sanitize.py` 注释做 **`img` + `res.cloudinary.com` 域白名单**，而不是直接放开 `img`（否则等于开放任意外链图片/追踪像素）。

## 12. `CatService.GetOrSave(name, False)` 会 AttributeError

未命中时 `result` 是 `None`，而 `status=False` 走 `else: id = result.id`。当前调用方全部传 `True`。不要在“只查不建”的场景传 `False`，那种场景应该用 `GetByName`。

## 13. 通用缓存工具目前没人用

`config/cache.py` 定义了 `get_cache_key` / `get_from_cache` / `set_to_cache` / `delete_cache` / `delete_cache_pattern`，但**没有任何 service 调用**。当前没有接口级响应缓存。改性能前先确认代码，不要凭函数名假设某接口已缓存。

`delete_cache_pattern` 用 `SCAN` 而不是 `KEYS`；反序列化用 `json.loads`，不用 pickle/yaml。

## 14. Cloudinary 缺失时的报错文案与行为不符

`config/security.py` 在 Cloudinary 三项缺失时抛的文案写“图片上传将回退到本地文件系统”，**实际行为是 import 期直接 raise，没有本地回退**。这是已知历史包袱。看到这段文案不要以为本地能用。

## 15. 后台文章详情不走响应信封

`GET /admin/article/{id}` → `ArticleService.GetId(id, status=True)` 直接返回 `to_admin_detail(...)` 裸 dict，没有 `{msg, code, data}`。管理端 `useApi` 用“同时有 `data` 和 `code` 才拆信封”来兼容。新增管理端详情接口时要么统一走 `info()`，要么记得同步前端。

## 16. 登出响应是嵌套的

`AuthService.Logout` 返回 `info(data={"code":200, "msg":"退出成功"})`，`code`/`msg` 在 `data` 里。前端不依赖这个结构，但别把它当标准信封。

## 17. 空串要归一成 NULL

文章封面、头像、简介等可空字段落库前都做 `value or None`。否则库里会同时存在 `""` 和 `NULL` 两种“空”，前端判断和图片清理逻辑都得兼容两套。新增可空字段时照做。

## 18. `ArticleSaveRequest.path` 可空，但数据库 NOT NULL

schema 里 `path: Optional[str] = None`，DB 列是 `NOT NULL`。不传 `path` 会在插入时触发 1048，被 `_conflict_detail` 翻译成 409“必填字段为空”。前端必须传 `path`。

## 19. 异步 session 下不要触发懒加载

`Article.category` 是 `lazy="selectin"`，但详情查询仍显式 `noload(Article.category)`。如果在异步上下文里访问未加载的关系（例如 `article.category.name`），会抛 `MissingGreenlet` / `StatementError`。

同理：`rollback()` 会 expire 所有持久化实例。异常路径里若还要用主键，必须在操作前先存局部变量（`UserService.Edit` / `RemoveSelf` 的 `user_id = user.id` 就是这个原因）。

## 20. 列表关键词搜索要转义 LIKE 通配符

`AdminList` 的 `keyword` 先替换 `\`，再替换 `%` 和 `_`，并使用 `escape="\\"`。顺序不能反，否则会把新加的转义反斜杠再转一遍，导致搜索不到。

## 21. 时间字段是 naive 本地时间

Python 侧 `datetime.now`、SQL 侧 `CURRENT_TIMESTAMP`，没有时区归一。JSON 输出不带时区，前端按本地时间展示。跨时区部署要单独处理，别假设有 UTC。

## 22. 测试目录与断言已过期

- `tests/` 未纳入版本控制，`pytest` 未安装（装之前先问用户）。
- `tests/test_smoke.py` 的复数路由断言与当前单数路由不符，处于失败状态。
- `tests/README.md` 的字段契约还写着 `thumbnail`，实际返回是 `cover`。

动测试前先按现状核对，别把失败用例当成“代码坏了”。

## 23. 生产不要直接跑 `main.py`

`main.py` 里是 `uvicorn.run("main:app", reload=True, ...)`。reload 只适合开发。生产用外部 uvicorn/gunicorn 并关闭 reload。

## 24. CORS 默认值会被 `.env` 整体覆盖

`CORS_ORIGINS` 默认 `http://localhost:3000,http://localhost:3001`。一旦 `.env` 里显式配置，默认值整体失效。只配 3000 会导致管理端（3001）所有请求被浏览器拦截。

## 25. Redis 连接是硬编码的，且机器上可能有两个 Redis

`config/cache.py` 固定 localhost:6379 / db 0 / 无密码 / 连接池 20。不要外置成 `REDIS_URL`（用户的明确决定）。

Windows 上还可能有一个同名服务 `Redis`（AUTO_START）指向旧版 3.0.504，会顶替 8.10.2。排查“限流不生效 / Lua 报错”先 `sc qc Redis`。

限流 Lua 已兼容 Redis 3.0+（`INCR` + 仅首次 `EXPIRE`），不再强依赖 7.0。

## 26. 状态值有三套，别混用

| 对象 | 取值 |
| :--- | :--- |
| 文章 | `1` 正常 / `2` 隐藏 / `3` 草稿 |
| 评论 | `0` 待审核 / `1` 正常 / `2` 屏蔽 |
| 用户 | `0` 禁用 / `1` 正常 / `is_admin` 单独 `0/1` |

文章与评论的常量在各自模型文件顶部**重名**，`models/__init__.py` 导出评论侧时加了 `COMMENT_` 前缀。

## 27. 管理端列表不带 `content`

`to_admin_preview` 不含正文。`ArticlePreview` 在点“预览”时再单发一次 `GET /admin/article/{id}`，不要给列表加批量预取（列表大时会把整个正文库拉进内存）。

## 28. 图片清理顺序与命名空间

见 `images.md`，这里只列红线：

- 先 commit，后销毁云端图，顺序不能反。
- `destroy_image` 不抛异常；失败只告警。
- 删除只允许 `fishmo_upload/` 前缀。
- URL 反推 `public_id` 必须同时校验主机、账号路径、`fishmo_upload/` 命名空间。
- 上传/销毁必须走 `run_in_threadpool`。

## 29. 验证码用途不能混用

Redis key 带 `purpose`（`register` / `delete`）。注册码不能注销，注销码不能注册。新增用途要同步 `services/email.py` 的 `_PURPOSES` 与 `_MAIL_TEMPLATES`，否则会拼出无模板 key 或发不出邮件。

## 30. `comment.user_email` 是死列

模型和表里都有，但代码从不写入、从不返回。不要因为看到列就以为评论会收集邮箱；也不要顺手把它加进返回体。

## 31. 死代码不要当入口

- `utils/verify.py` 的 `verify_login` 没有调用方。
- `schemas/user.py` 的 `ResetPwdRequest` 没有调用方（密码重置流程尚未实现）。

看到它们时不要以为存在“另一条登录/重置路径”。

## 附：历史 CODE_REVIEW 项的当前状态

`CODE_REVIEW.md` 是 2026-10-20 的快照，不能当现状。按当前代码复核：

| 项 | 状态 |
| :--- | :--- |
| B-1 导入链断裂 | **已修**（`import main` 正常，30 条路由） |
| B-3 浏览量回写缺 WHERE | **已修**（`sync_to_db` 已带 `WHERE id = :b_id`） |
| B-2 账号维度登录限流可定向锁账号 | **仍存在**（见第 8 条） |
| M-4 回复的回复入库但不显示 | **仍存在**（见第 9 条） |

其余 M 项未在本轮逐条复核；动认证、限流、浏览量之前先看 `CODE_REVIEW.md`，但**以代码为准**。