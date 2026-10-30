# 测试

`tests/` 目录**未纳入版本控制**（在 `.gitignore` 里），依赖 `pytest` + `httpx`（`httpx` 已装，**`pytest` 尚未安装**；装之前先问用户）。`tests/README.md` 是原始设计说明，改测试前先读它。

## 运行

```bash
# 从仓库根目录跑（conftest.py 自己把 app/ 注入 sys.path）
.venv/Scripts/python.exe -m pytest tests/ -v

# 只跑不依赖外部服务的冒烟组
.venv/Scripts/python.exe -m pytest tests/test_smoke.py -v

# 按名字筛
.venv/Scripts/python.exe -m pytest tests/ -k "logout or token" -v

# 需要真实登录链路时额外传管理员账号（密码哈希存储，测试无法推导明文）
TEST_USER_EMAIL=admin@example.com TEST_USER_PASSWORD='...' \
  .venv/Scripts/python.exe -m pytest tests/ -v
```

## 分档 marker

未满足条件的用例 **skip 而不是 fail**：

| marker | 含义 |
| :--- | :--- |
| （无） | 纯逻辑，不碰外部依赖，总是运行 |
| `requires_db` | 需要 MySQL 可连接 |
| `requires_data` | 需要 `article` 表有 `status=1` 的数据 |
| `requires_redis` | 需要本地 Redis 可连接 |
| `requires_account` | 需要 `TEST_USER_EMAIL` / `TEST_USER_PASSWORD` |

写完新用例记得在 `conftest.py` 的 `pytest_configure` 里注册 marker。

## 两条必须遵守的实现约束

1. **`app_client` 是 session 作用域的**。Starlette 的 `TestClient` 只有作为上下文管理器使用才复用同一个事件循环；每次请求新建 portal 会让 async 引擎连接池跨事件循环复用连接，报 `attached to a different loop`。
2. **不引入 `pytest-asyncio`**。测试本身不写 `async def`，全部通过同步 `TestClient` 驱动。需要读库断言时用独立的**同步**引擎（`pymysql`），与应用自身的 async 引擎隔离。

## 各文件覆盖

### `test_smoke.py` —— 不依赖外部服务

拦“低级但致命”的问题：

- `test_app_imports` —— 导入链完整性。
- `test_expected_route_registered` —— 关键路由已注册。
- `test_dynamic_route_registered_last` —— 动态兜底路由在最后。
- `test_openapi_schema_generates` —— OpenAPI 能生成。
- `test_list_rejects_out_of_range_paging` —— 分页参数越界。
- `test_login_rejects_malformed_payload` —— 登录入参校验。
- `test_logout_requires_token` / `test_authenticated_endpoint_rejects_bad_token` —— 401 行为。
- `test_token_roundtrip` / `test_token_rejects_invalid` / `test_token_rejects_tampered_signature` —— JWT 签发/校验/防篡改。
- `test_password_hash_uses_argon2` —— 哈希算法。
- `test_unknown_account_verification_cost_matches_real_one` —— 未知账号也跑等价开销校验（时间侧信道）。

### `test_article_api.py` —— 需要文章数据

列表/详情契约、分页、排序、404、非公开文章不可达等。**注意该文件大量使用复数路由 `/articles/...`，与当前单数路由 `/article/...` 不符，处于过期状态。**

### `test_auth_api.py` —— 分档依赖

未知邮箱 401、错误信息不泄露账号存在性、失败不带 token、登录限流 429、按账号限流、成功令牌在响应体、令牌可用、登出立即失效、已存在账号错密码 401。

## 已知失效/过期项

- `tests/test_smoke.py` 的 `test_expected_route_registered` 与 `test_dynamic_route_registered_last` 断言的是**复数路由**（`/articles/`、`/articles/id/{id}`），代码注册的是单数（`/article/`、`/article/{path}`）——仍处于失败状态，**不能当有效护栏**。
- `tests/README.md` 的文章字段契约还写着 `thumbnail`，实际返回是 `cover`。
- `tests/README.md` 的“尚未完成”说仓库没有 `requirements.txt`，但根目录现在已有（只含后端运行时依赖）。
- `test_article_api.py` 的 `/articles/id/<数字>` 用例同样过期。

动测试前先按当前代码核对，别把失败用例当成“代码坏了”。

## 校验手段的上限

- `import main` + 路由数量只证明**导入链通**，不证明行为正确。
- `npm run build`（web/admin）不跑类型检查。
- 项目曾踩过“手搓等价语句 + `.compile()` 都验不出 SQLAlchemy 把 list 传给 ORM 实体 `update()` 会被改写成按主键批量更新”的坑。**要证明行为正确，必须实际驱动真实函数**（TestClient、真实 ORM 调用或跑测试），不能只做静态推演。

## 尚未接入的自动化

- 没有 lint / 类型检查门禁（`ruff` 的 F401/F811、`mypy`）。review 里“未使用导入”“视图函数重名”这类问题工具能全自动拦下。
- 没有覆盖率门禁。
- 没有 CI；测试只在本机按需运行。

这些属于“可被工具兜底”的检查项，建议逐步纳入 CI，把人工审核留给逻辑与设计。