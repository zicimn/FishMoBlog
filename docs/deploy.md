# 线上部署（nginx + Nuxt SSR + FastAPI）

线上只有两个进程 + 一个 nginx：

```text
浏览器 ──▶ nginx :80/:443 (www.fishmo.top)
             ├─ /api/*  ──proxy_pass──▶ FastAPI 127.0.0.1:8000
             ├─ 静态文件 ──root──▶ /www/wwwroot/default/blog/.output/public
             └─ 其他     ──proxy_pass──▶ Nuxt SSR 127.0.0.1:3000
```

管理端**不部署**。Redis 与 MySQL 与后端同机或内网。

## nginx 结构

`nginx.conf` 在 `.gitignore` 里，不在版本控制中，改之前先备份。关键段：

```nginx
root /www/wwwroot/default/blog/.output/public;
index index.html index.htm;

location ^~ /api/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### `/api/` 末尾的斜杠不能省

`proxy_pass http://127.0.0.1:8000/;` 末尾的 `/` 表示**剥掉 `/api/` 前缀**：

- 浏览器请求 `/api/article/?page=1` → 后端收到 `/article/?page=1`；
- 如果写成 `proxy_pass http://127.0.0.1:8000;`（无斜杠），后端会收到 `/api/article/`，而 FastAPI 没有这个路由 → 404。

前端生产构建把 `public.apiBase` 覆盖成 `/api`，所以浏览器侧所有请求都走这条规则。SSR 侧仍用私有的 `apiBaseServer`（默认 `http://127.0.0.1:8000`）直连后端，**不经过 nginx**。

### 其他段

- `listen 80` + `listen 443 ssl` + `http2 on`，证书路径在 `ssl_certificate` / `ssl_certificate_key`，域名 `www.fishmo.top`。
- 敏感文件/目录 404：`.env`、`.git`、`node_modules`、`.nuxt`、`requirements.txt`、`*.sql`、`CLAUDE.md`、`docker-compose.yml` 等都被正则拦掉。**不要把这些文件放进 web root。**
- 静态缓存：图片 30 天、js/css 12 小时；日志在 `/www/wwwlogs/`。
- 改完 nginx 必须 `nginx -t` 再 reload，否则配置错误会让整站 502/起不来。

## 构建与启动

### 前台（Nuxt SSR）

```bash
cd web
npm run build          # 产物：web/.output/public（静态）+ web/.output/server（SSR）
node .output/server/index.mjs   # 或 pm2 / systemd 托管，监听 3000
```

部署时：

1. **先停 dev / 旧进程**（或至少确保构建时没有 dev 在跑）。
2. `npm run build`。
3. **重启 Node 进程**。只替换文件不重启，旧进程仍持有旧模块与旧内存态。
4. 确认 `.output/public` 与 `.output/server` 是**同一次构建**的产物。

`nuxt build` 不跑类型检查，只证明“能构建”。要类型正确另跑 `npm run typecheck`（已知有一条 vue-router 解析告警，不影响退出码）。

### 后端（FastAPI）

```bash
cd app
../.venv/Scripts/python.exe main.py     # 仅开发；生产不要用这个
```

生产建议用外部 uvicorn/gunicorn 并关闭 reload：

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
```

（在 `app/` 目录下执行；`main:app` 依赖 `app/` 是包根，见 `app/README.md`。）

服务器上必须有完整的 `app/.env`（键名见 `app/getting-started.md`），缺任一必需项会在 import 期直接 raise。数据库表结构要按 `app/sql/*.sql` 手工建/改——**没有自动建表、没有 Alembic**。

Redis 连接参数硬编码 localhost:6379（`config/cache.py`），部署时 Redis 必须在同机 6379；不要把地址改成别的而不改代码。

### CORS

生产浏览器走同源 `/api`，**不需要 CORS**。`CORS_ORIGINS` 只在以下场景有用：

- 本机开发：`web` 直连 8000（源 `http://localhost:3000`）、`admin` 直连 8000（源 `http://localhost:3001`）；
- 如果你把前端单独部署到别的域名。

默认值是 `http://localhost:3000,http://localhost:3001`；一旦 `.env` 里显式配置，默认值整体失效。

## 排查“线上跑的还是旧构建”

按下面顺序查，基本能定位：

1. **Node 进程什么时候启动的？**
   ```bash
   pm2 list          # 或 systemctl status <service>
   ps -o lstart= -p <pid>
   ```
   进程启动时间早于构建时间 → 没重启，替换文件没用。

2. **`root` 指向对了吗？**
   ```bash
   ls -l /www/wwwroot/default/blog/.output/public
   ls -l /www/wwwroot/default/blog/.output/server
   ```
   `root` 必须是 `.output/public`，不是仓库根、不是 `web/`。`/` 又反代到 3000，所以静态资源（js/css/图片）由 nginx 直接从 `root` 取，SSR 页面由 Node 出。

3. **`public` 与 `server` 是不是同一次构建？**
   ```bash
   stat -c '%y %n' .output/public .output/server
   ```
   两次构建混用会出现：SSR 返回的 HTML 引用新 hash 的 JS，但 `public` 里还是旧文件 → 浏览器 404 / 白屏 / `Failed to fetch dynamically imported module`。**整个 `.output` 一起替换，不要只拷 `public`。**

4. **浏览器缓存**：js/css 缓存 12 小时、图片 30 天。新构建 hash 变了通常不会命中旧缓存；若怀疑缓存，硬刷新 / 无痕窗口验证。

5. **接口是不是真的到了后端？**
   ```bash
   curl -s https://www.fishmo.top/api/article/?page=1\&size=1 | head
   ```
   返回 `{msg, code, data}` 说明 `/api/` 反代正常；返回 HTML/404 说明前缀没剥掉、后端没起或 nginx 没 reload。

6. **端口监听**：
   ```bash
   ss -lntp | grep -E ':(3000|8000)\b'
   ```

7. **构建时打进了回环地址？** 如果浏览器控制台报 `ERR_CONNECTION_REFUSED` 到 `127.0.0.1:8000`，说明 `public.apiBase` 是本地值。生产构建应走 `$production` 覆盖成 `/api`；可用 `NUXT_PUBLIC_API_BASE=/api` 在运行时纠正，或重新构建。前端 `useApiBase` 对回环地址有防呆，会自动退回 `/api` 并打 `console.error`，但正确做法仍是修构建配置。

8. **nginx 配置改过没 reload？**
   ```bash
   nginx -t && nginx -s reload
   ```
   `nginx.conf` 是 gitignored，别在服务器上直接大改而没有备份。

## 部署检查清单

- [ ] `app/.env` 配齐（DB / SECRET_KEY / RESEND / Cloudinary），文件不进 web root。
- [ ] MySQL 表结构已按 `app/sql/*.sql` 建好；新增列已手工 `ALTER`。
- [ ] Redis 在 6379 可用（确认不是旧版服务顶替）。
- [ ] 后端 `uvicorn main:app` 在 8000 监听，`/openapi.json` 返回 200。
- [ ] 前端 `npm run build` 完成，`.output/public` 与 `.output/server` 同批。
- [ ] Node 进程已用新产物重启，3000 监听。
- [ ] nginx `root` 指向 `.output/public`，`/api/` 的 `proxy_pass` 末尾有斜杠，`nginx -t` 通过并 reload。
- [ ] `curl https://<域名>/api/article/?page=1` 返回信封 JSON。
- [ ] 浏览器硬刷新后页面正常，控制台无“连 127.0.0.1”的报错。
- [ ] 管理端只在本地跑，3001 / 8000 不对公网开放。