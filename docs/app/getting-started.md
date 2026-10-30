# 后端启动与环境

## 前置条件

| 组件 | 版本 / 位置 | 说明 |
| :--- | :--- | :--- |
| Python | 3.12.7 | 虚拟环境在仓库根目录 `.venv/`，不是 `app/.venv` |
| MySQL | 5.7+ / 8.x | 字符集 `utf8mb4`，库需事先建好 |
| Redis | 建议 8.10.2 | 本机路径 `D:\Redis\redis-windows-8.10.2\redis-server.exe`，监听 6379、无密码 |
| 依赖 | 仓库根目录 `requirements.txt` | 只含后端运行时直接依赖，版本用 `==` 固定 |

> 往 `.venv` 装新包前先问用户；新增后端运行时依赖后要同步 `requirements.txt`。目前 **没有** `pyproject.toml`、没有 `.env.example`、`pytest` / `ruff` / `mypy` 都未安装。

## 环境变量：`app/.env`

`app/config/security.py` **显式**按文件位置加载 `app/.env`（`Path(__file__).parents[1] / ".env"`），不依赖 cwd，也不走 dotenv 的向上查找。所以：

- 文件必须叫 `app/.env`，放在后端目录下。
- 缺任一必需项都会在 **import 期直接 `raise ValueError`**，服务起不来。看到 `import main` 报环境变量错，先查 `.env`。

### 变量清单

下表只列键名与用途；**真实值一律不写进文档**，示例均为占位符。

| 变量 | 必需 | 用途 | 占位示例 |
| :--- | :--- | :--- | :--- |
| `ASYNC_DATABASE_URL` | 是 | MySQL 异步连接串，`mysql+aiomysql://<user>:<pwd>@<host>:3306/<db>?charset=utf8mb4` | `mysql+aiomysql://user:password@127.0.0.1:3306/blog?charset=utf8mb4` |
| `SECRET_KEY` | 是 | JWT HS256 签名密钥 | `change-me-to-a-long-random-string` |
| `RESEND_API_KEY` | 是 | Resend 邮件服务密钥，验证码邮件用 | `re_xxxxxxxxxxxxxxxx` |
| `RESEND_FROM` | 否 | 发件人地址，默认 `onboarding@resend.dev` | `noreply@yourdomain.com` |
| `CLOUDINARY_CLOUD_NAME` | 是 | Cloudinary 云名 | `your-cloud-name` |
| `CLOUDINARY_API_KEY` | 是 | Cloudinary API Key | `000000000000000` |
| `CLOUDINARY_API_SECRET` | 是 | Cloudinary API Secret | `your-api-secret` |
| `CORS_ORIGINS` | 否 | 逗号分隔的允许来源，默认 `http://localhost:3000,http://localhost:3001` | `http://localhost:3000,http://localhost:3001` |

几个容易踩的点：

- **`RESEND_FROM` 必须是可选项**。新增一个必需变量会让现有 `.env` 整体 import 失败。
- 默认发件人 `onboarding@resend.dev` 是 Resend 测试发件人，**只能投递到 API key 所属账号的邮箱**。上线要换成已在 Resend 验证过域名的地址，否则验证码发不到用户。
- `CORS_ORIGINS` 的约定格式是**逗号分隔的单字符串**。`.env` 里一旦显式配置，会整体覆盖默认值——只写 3000 会把管理端（3001）挡掉。
- **Cloudinary 三项缺任意一项都会在 import 期 raise**。`config/security.py` 的报错文案写的是“图片上传将回退到本地文件系统”，**实际行为是直接 raise，没有本地回退**。文案与行为不一致，属已知历史包袱。
- **Redis 连接参数是硬编码在 `config/cache.py` 里的**（localhost、6379、db 0、无密码、连接池上限 20），这是用户的明确决定，不要把 `REDIS_URL` 外置进去。

## 启动

```bash
cd app && ../.venv/Scripts/python.exe main.py
```

`main.py` 内置 uvicorn：

```python
uvicorn.run("main:app", reload=True, reload_excludes=["*.log", "__pycache__/*"])
```

监听 `main:app`，默认 8000，reload 已开。**生产环境请用外部 uvicorn/gunicorn 起（关闭 reload）**，别直接跑这个脚本。

lifespan 里还会启动后台任务 `ArticleViewCounter.periodic_sync_to_db()`，每 300 秒把 Redis 里的浏览量增量回写 MySQL，进程退出时 cancel。Redis 挂了它只会报错、不会让服务起不来。

## 导入链自检

改完模型 / schema / 路由后最快的回归：

```bash
cd app && ../.venv/Scripts/python.exe -c "import main; print(len(main.app.routes))"
# 期望：30
```

它只证明**导入链通**，不证明接口行为正确。要证明行为得实际驱动函数或跑测试（见 `../testing.md`）。项目曾踩过“手搓等价语句 + `.compile()` 都验不出 SQLAlchemy 把 list 传给 ORM 实体 `update()` 会被改写成按主键批量更新”的坑。

## 数据库：没有自动建表，也没有迁移

全仓**没有** `create_all`，**没有** Alembic。改模型不会同步数据库，表结构变更必须手工跑 SQL：

- `app/sql/blog.sql` —— 主表（article / category / comment / user 等）的建表语句。
- `app/sql/msg.sql` —— 留言表 `msg` 与唯一索引 `uk_msg_user`。
- `app/sql/build.sql` —— 建库/基础结构。

这些 SQL 文件在 `.gitignore` 里，**不会随仓库分发**。换机器部署时要照着它们手工建表；新增列（例如 `article.cover_public_id`）也要手工 `ALTER TABLE`。

### 连接池参数（`config/db.py`）

| 参数 | 值 | 含义 |
| :--- | :--- | :--- |
| `pool_size` | 10 | 常驻连接数 |
| `max_overflow` | 20 | 峰值可额外创建的连接数 |
| `pool_recycle` | 3600 | 连接回收秒数（防 MySQL `wait_timeout` 断连） |
| `pool_timeout` | 30 | 取连接的等待上限 |
| `pool_pre_ping` | True | 取连接前探活 |
| `connect_timeout` | 10 | 建连超时 |

`get_db` 的开销控制：**只有 session 存在待写变更（`new` / `dirty` / `deleted`）时才 commit**，避免 GET 也开写事务；`expire_on_commit=False`，commit 后对象仍可读。

## Redis 的两个坑

1. **Redis ≥ 7 已不是硬要求**。固定窗口限流从 `EXPIRE ... NX` 改成了 Lua（`INCR` + 仅首次 `EXPIRE`），3.0+ 都能用。日常仍建议用 8.10.2。
2. **机器上可能有两个 Redis**。除了 `D:\Redis\redis-windows-8.10.2\redis-server.exe`，还可能存在一个同名 Windows 服务 `Redis`（AUTO_START），指向旧版 `D:\Redis-x64-3.0.504\redis-server.exe`。启动那个服务会顶替 8.10.2 占用 6379。排查“限流不生效 / Lua 报错”时先确认是谁在监听：

```bash
sc qc Redis
```

## 验证服务真的起来了

```bash
curl http://127.0.0.1:8000/openapi.json -o /dev/null -w "%{http_code}\n"   # 200
```

或者直接看 `http://127.0.0.1:8000/docs`。前台 `web/` 的 SSR 在后端没起时会带着错误态返回，页面自带错误面板与重试，不算后端回归。