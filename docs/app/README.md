# 后端总览（`app/`）

FastAPI 0.133 + SQLAlchemy 2.0 异步 ORM + MySQL(aiomysql) + Redis。入口 `app/main.py`，进程内跑 uvicorn（`main:app`），并在 lifespan 里启动浏览量回写的后台任务。

## 最重要的一条：`app/` 才是包根

`app/` 下的模块都是**顶层包**，import 一律写 `from config import ...`、`from models import ...`、`from utils import ...`，**不存在 `app.` 前缀**。因此：

- 所有命令必须先 `cd app`（或把 `app/` 加进 `sys.path`，`tests/conftest.py` 就是这么做的）。
- 在仓库根目录直接 `python -c "import main"` 会失败。
- 跨层引用一律用绝对导入（`from deps import ...`）。写 `from ..deps import ...` 会报：

```text
ImportError: attempted relative import beyond top-level package
```

改完模型 / schema / 路由后，最快的自检是：

```bash
cd app && ../.venv/Scripts/python.exe -c "import main; print(len(main.app.routes))"
```

正常输出 **30**（26 条业务路由 + FastAPI 自带的 `openapi` / `docs` / `oauth2-redirect` / `redoc` 4 条）。数字变了先查是不是漏了 `include_router` 或新增了路由。

## 四层请求链路

```text
main.py                FastAPI 实例 + CORS + lifespan（起浏览量回写任务）+ include_router(service_router)
  └─ api/__init__.py   service_router：汇总 article / auth / user / comments / admin / msg 六个 router
       └─ api/*.py     只做三件事：定义 router、声明依赖、把 AppError 转成 HTTPException
            └─ deps.py Depends 工厂：GetXxxService 注入 AsyncSession；GetCurrentUser / GetAdminUser 做鉴权
                 └─ services/*.py  业务逻辑，抛 AppError，绝不碰 HTTPException
                      └─ models/*.py  SQLAlchemy 模型
```

各层职责固定，改东西按层落位：

| 位置 | 做什么 | 不做什么 |
| :--- | :--- | :--- |
| `api/*.py` | 定义 router / prefix、声明依赖、`try/except AppError → HTTPException`、调 service | 不写业务判断、不拼 SQL |
| `deps.py` | 生成 service 实例、解析当前用户 / 管理员 | 不写业务逻辑 |
| `services/*.py` | 业务编排、抛 `AppError` 子类、`db.commit()` | 不 import `HTTPException` |
| `models/*.py` | 表结构与状态常量 | 不写查询业务 |
| `schemas/*.py` | Pydantic 入参模型 + 返回 dict 的普通转换函数 | **不是** `response_model` 层 |

### 路由层逐端点 try/except 是既定风格

每个端点都长这样，照抄即可：

```python
try:
    return await service.GetId(id)
except AppError as e:
    raise HTTPException(status_code=e.status_code, detail=e.msg)
```

状态码由异常类自带，不要手写魔法数字（见 `docs/app/gotchas.md` 的异常类表）。`Conflict`（409）是为唯一索引冲突新增的，**别用 `OpError` 顶替**：`OpError` 语义是“无权限”，前端会翻成“需要管理员权限”。

## 目录职责

```text
app/
├─ main.py                  FastAPI 实例、CORS、lifespan、uvicorn 启动
├─ api/                     路由层（article / auth / user / comments / admin / msg + __init__ 汇总）
├─ deps.py                  Depends 工厂与鉴权
├─ services/                业务逻辑
│  ├─ article.py            文章 + 栏目编排
│  ├─ auth.py               登录 / 注册 / 登出
│  ├─ user.py               资料编辑 / 用户列表 / 注销
│  ├─ comment.py            评论
│  ├─ msg.py                留言板
│  ├─ email.py              验证码（Redis）与 Resend 发信
│  ├─ image.py              Cloudinary 上传/删除编排
│  └─ category.py           栏目 GetOrSave
├─ models/                  SQLAlchemy 模型 + 状态常量（__init__ 汇总导出）
├─ schemas/                 Pydantic 入参 + to_xxx 转换函数
├─ config/                  聚合出口（__init__.py）：db / cache / security
├─ utils/                   聚合出口（__init__.py，白名单）：responsed / verify / sanitize / counter / cloudinary
└─ sql/                     手工建表/改表 SQL（gitignore）
```

### `config/` 与 `models/`、`utils/` 都是聚合出口

- 全项目一律 `from config import get_db, Base, rate_limit, ...`，**不要** `from config.db import ...`。
- `from models import Article, User, STATUS_PUBLIC`。状态常量定义在各模型文件顶部，文章与评论的常量**重名**，评论侧导出时加了 `COMMENT_` 前缀别名。
- `utils/__init__.py` 是**白名单**：新增符号必须显式导出，漏了会让 `from utils import ...` 直接失败。
  - `utils/responsed.py` —— `AppError` 体系 + `info()`（不是 `utils/err.py`，那个文件已删）。
  - `utils/verify.py` —— JWT 与 argon2。
  - `utils/sanitize.py` —— nh3 消毒。
  - `utils/counter.py` —— 浏览量计数。
  - `utils/cloudinary.py` —— 图片转换 / 上传 / 销毁。

## 响应信封

统一由 `utils/responsed.py` 的 `info()` 拼：

```json
{ "msg": "成功", "code": 200, "data": { } }
```

`code` 是业务码（默认 200），`msg` 是给人看的中文，`data` 是载荷。**返回的是裸 dict，不是 Pydantic 模型**——项目刻意暂缓了 `response_model`，不要自作主张加。

唯一的例外：`GET /admin/article/{id}` 的 service 方法 `GetId(status=True)` 直接返回 `to_admin_detail(...)` 的**裸 dict**（没有 `{msg, code, data}` 信封）。管理端 `useApi` 专门兼容了这一点（见 `admin.md`）。

## 已知会踩的点（详见 `gotchas.md`）

- Service 方法一律 **PascalCase**（`GetId` / `AdminList` / `Save` / `GetOrSave` / `Upload`），这是既有风格，别“顺手规范化”成 snake_case，会牵动所有调用方。
- `api/article.py` 的 `/{path}` 是动态兜底路由，**必须注册在最后**。
- `remove` / `edit` 必须**显式 `await db.commit()`**，只 `flush()` 会被 `get_db` 的提交条件静默回滚。
- 可空字段用 `model_fields_set` 判断“不改 vs 清空”，不是真值判断。
- Redis 不可用时的降级策略是**故意不一致**的：限流/黑名单失败开放，登出失败关闭。
- 分类状态常量：文章 `1/2/3`（`STATUS_PUBLIC = (1,)`），评论 `0/1/2`；两套不通用。