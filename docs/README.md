# 项目文档

个人博客的完整文档。仓库里实际有三个可独立运行的应用：

| 目录 | 形态 | 技术栈 | 端口 | 部署 |
| :--- | :--- | :--- | :--- | :--- |
| `app/` | FastAPI 后端 | Python 3.12.7 / FastAPI 0.133 / SQLAlchemy 2.0 异步 / MySQL(aiomysql) / Redis | 8000 | 线上（systemd / 进程 + nginx 反代） |
| `web/` | 博客前台 | Nuxt 4（**保留 SSR**）/ Vue 3 / Tailwind v4 | 3000 | 线上（nginx `www.fishmo.top`） |
| `admin/` | 管理端 | Nuxt 4（`ssr: false` 纯 SPA）/ Pinia / Tiptap | 3001 | **不部署**，仅本机使用 |
| `tests/` | 测试 | pytest + httpx（未纳入版本控制，pytest 未安装） | - | 本地 |

前台与管理端都是独立的 Nuxt 应用，**直接打后端 HTTP 接口，没有 BFF 层**。三者关系只有一个方向：浏览器 → Nuxt 页面 → FastAPI；后端不认识前端。

## 文档索引

### 后端 `app/`

- [`app/README.md`](app/README.md) —— 后端总览：`app/` 作为包根、四层请求链路、目录职责、响应信封与错误处理约定。
- [`app/getting-started.md`](app/getting-started.md) —— 环境变量（只列键名）、启动、导入链自检、无自动建表/无迁移的现状、Redis 注意事项。
- [`app/api.md`](app/api.md) —— 全部 26 条业务路由清单（路径 / 方法 / 鉴权 / 返回），限流参数，路由顺序约束。
- [`app/services-article.md`](app/services-article.md) —— 文章与栏目的业务规则：列表/详情/保存/编辑/删除、状态过滤、浏览量自增、图片引用清理、并发冲突映射。
- [`app/services-auth-user.md`](app/services-auth-user.md) —— 登录/注册/登出、JWT 设计、邮件验证码、用户资料与账号注销。
- [`app/services-comment-msg.md`](app/services-comment-msg.md) —— 评论（含后台列表）与留言板：权限、消毒、限流、一人一条。
- [`app/images.md`](app/images.md) —— Cloudinary 图片上传/删除全链路（后端四道闸 + 前端三态契约）。
- [`app/data-model.md`](app/data-model.md) —— 表结构、状态常量、可空字段语义、索引与外键、手工 SQL。
- [`app/gotchas.md`](app/gotchas.md) —— 后端踩坑清单（导入、commit、路由顺序、Redis 降级、计数、已知未修问题）。

### 前端

- [`web.md`](web.md) —— 博客前台：SSR、两个 API 基址、页面、登录态、评论/留言板、关于页、构建校验的边界。
- [`admin.md`](admin.md) —— 管理端：SPA、页面清单、接口清单、唯一 HTTP 出口、图片上传三态、编辑器。
- [`deploy.md`](deploy.md) —— 线上部署：nginx 结构、构建产物、`/api/` 反代、重启进程、排查“线上跑的还是旧构建”。

### 其他

- [`testing.md`](testing.md) —— 测试套件的分档设计与已知失效断言。

## 一页纸全貌

```text
                     ┌──────────────────────────────┐
  浏览器              │  web/  (Nuxt 4 SSR, :3000)    │
  www.fishmo.top ───▶│  article / guestbook / about  │
                     └───────────────┬──────────────┘
                                     │ HTTP（useFetch，baseURL 见 web.md）
                     ┌───────────────▼──────────────┐
  管理员本机          │  app/  (FastAPI, :8000)       │
  :3001 ────────────▶│  api → deps → services → models│
  admin/ (SPA)       └───┬───────────┬───────────┬──┘
                         │           │           │
                    MySQL(aiomysql) Redis    Cloudinary / Resend
```

- **浏览器 → 后端**：前台 SSR 在服务端发起请求（`apiBaseServer`，默认 `http://127.0.0.1:8000`），浏览器侧走 `public.apiBase`；生产构建下 `public.apiBase` 被覆盖为 `/api`，由 nginx 反代到 8000。
- **管理端 → 后端**：纯 SPA，`apiBase` 硬编码 `http://127.0.0.1:8000`，只在本机跑，所以后端 `CORS_ORIGINS` 必须包含 `http://localhost:3001`。
- **鉴权**：JWT（HS256，7 天，载荷带 `jti`）放在请求头 `Authorization: Bearer <token>`；令牌本身从登录/注册**响应体的 `access_token` 字段**返回，不走响应头。前端各存各的 localStorage。
- **权限**：JWT 里**没有** `is_admin`，每次请求回库取用户再判定；管理端接口由 `api/admin.py` 的 router 级依赖统一拦截。

## 本地起四个服务

```bash
# 1. Redis（前台运行，监听 6379、无密码）
D:/Redis/redis-windows-8.10.2/redis-server.exe

# 2. 后端（main.py 内置 uvicorn，监听 main:app，reload 已开）
cd app && ../.venv/Scripts/python.exe main.py

# 3. 前台 http://localhost:3000
cd web && npm run dev

# 4. 管理端 http://localhost:3001
cd admin && npm run dev
```

仓库根目录曾有一个 `run.bat` 用 Windows Terminal 一次开四个标签，但它在 `.gitignore` 里，新克隆的仓库没有。

## 本仓库的“隐形”文件

以下内容**都在 `.gitignore` 里，不进版本控制**，新克隆的仓库不会有：

`CLAUDE.md`、`CODE_REVIEW.md`、`tests/`、`docs/`、`nginx.conf`、`app/sql/`、`run.bat`、`app/.env`。

由此带来的两个直接后果：

1. **没有迁移文件**：`app/sql/*.sql` 是本机手工执行用的建表/改表脚本，代码里没有 `create_all`、没有 Alembic。换机器部署要照着这些 SQL 手工建表。
2. **改这些文件不会出现在 `git status` 里**，别以为改动丢了。

## 核对基线

改动后最快的回归手段：

```bash
cd app && ../.venv/Scripts/python.exe -c "import main; print(len(main.app.routes))"
# 正常输出 30（26 条业务路由 + FastAPI 自带 openapi/docs/oauth2-redirect/redoc 4 条）
```

它只证明**导入链通**，不证明行为正确。行为验证要实际驱动真实函数或跑测试（见 `testing.md`）。