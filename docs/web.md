# 博客前台（`web/`）

Nuxt 4 + Vue 3 + TypeScript + Tailwind v4，**保留 SSR**（前台要 SEO，与 admin 的纯 SPA 相反）。`srcDir = app/`，dev 端口 **3000**，线上由 nginx 反代到 `www.fishmo.top`。没有 Nitro 业务接口，所有数据直接打 FastAPI。

## 两个 API 基址（最容易踩）

`nuxt.config.ts` 用 `runtimeConfig` 区分服务端与浏览器：

| 配置 | 可见性 | 默认值 | 生产值 |
| :--- | :--- | :--- | :--- |
| `apiBaseServer` | **私有**，不下发浏览器 | `http://127.0.0.1:8000` | 同左（后端同机时） |
| `public.apiBase` | 公开，会进浏览器 bundle | `http://127.0.0.1:8000` | `/api` |

`$production` 段把 `public.apiBase` 覆盖为 `/api`，`apiBaseServer` 仍直连后端。运行时还可用环境变量覆盖：`NUXT_PUBLIC_API_BASE`（浏览器侧）、`NUXT_API_BASE_SERVER`（SSR 侧）。

`composables/useApiBase.ts`：

```ts
if (import.meta.server) return config.apiBaseServer || config.public.apiBase
return config.public.apiBase   // 客户端
```

### 为什么 SSR 不能直接用 `/api`

Nuxt 的 `useFetch` 在服务端遇到相对 request + 相对 baseURL 时会改用 `useRequestFetch()`，而 Nitro 的本地 fetch 会把 `/api` 当作 Nuxt 自己的路由（本项目没有这个路由），请求不会经过 nginx，最终 404。所以服务端必须用绝对地址。

反过来，`apiBaseServer` 是私有配置，**不会序列化到浏览器**，避免把内网后端地址暴露给访客。

### 回环地址防呆

如果构建产物把 `127.0.0.1` / `localhost` 打进了 `public.apiBase`（旧产物，或 `NUXT_PUBLIC_API_BASE` 误设），访客浏览器会去连**他自己机器**的 8000 端口，必然 `ERR_FAILED` + CORS 报错。`useApiBase` 在客户端做了判断：页面本身不在回环地址上、而 base 指向回环地址时，打一条 `console.error` 并退回同源 `/api`。

`useApiBaseLabel()` 只用于界面文案（“请确认后端已启动（…）”），取 `public.apiBase`，保证 SSR 与客户端文本一致。

## 页面

| 路由 | 文件 | 数据 |
| :--- | :--- | :--- |
| `/` | `pages/index.vue` | 个人主页卡片 + 最新文章，每页 **9** |
| `/articles` | `pages/articles/index.vue` | 全部文章列表，每页 **12** |
| `/article/[path]` | `pages/article/[path].vue` | 文章详情 + 目录 + 评论区 |
| `/guestbook` | `pages/guestbook/index.vue` | 留言板，每页 **10** |
| `/about` | `pages/about.vue` | 关于页，正文来自 `web/app/content/about.md` |

数据获取一律：

```ts
const { data, pending, error, refresh } = await useFetch<Envelope<T>>(url, {
  baseURL: apiBase,
  query: { ... },
})
```

后端没起时 SSR 会带着错误态返回，页面自带错误面板与重试按钮。

### 文章详情

- `GET /article/{path}`，`watch: [path]`。该接口会**自增浏览量**，刷新/来回导航都会 +1，这是既有行为，**不要在 web 侧加“只看一次”的计数**。
- 404 时在 SSR 阶段 `setResponseStatus(event, 404)`。
- `utils/content.ts` 的 `buildToc(html)` 在渲染前给 `h1`–`h4` 注入 `id` 并抽出目录（库里的 HTML 没有 id）；`stripHtml` 用于摘要/纯文本。
- 正文用 `v-html` 渲染。文章是管理员写的原始 HTML，后端**不做消毒**（见 `app/gotchas.md`）。

### 文章列表

`GET /article/`，参数 `page` / `size` / 可选 `category_name`。分页用 `useFetch` 的响应式 query，`page` 变化自动重发。

## 登录态 `useAuth`

`composables/useAuth.ts`，用 `useState` 而不是 Pinia（前台只有令牌 + 用户两个值）：

| 状态 | 说明 |
| :--- | :--- |
| `auth-token` | JWT |
| `auth-user` | `{ id, email, username, avatar, bio, is_admin }` |
| `auth-ready` | 是否已尝试读 localStorage |

localStorage 键：`fishmo_access_token` / `fishmo_user`。

### SSR 不读 localStorage

SSR 阶段两个状态恒为空。`plugins/auth.client.ts` 在 `app:mounted` 后调用 `init()` 回填，避免服务端“未登录”与客户端首帧“已登录”不一致导致 hydration mismatch。**不要在 setup 里直接读 localStorage。**

初始化完成前 `ready=false`，评论框先渲染骨架，而不是闪一下“请登录”。

### 快照容错

- 只有令牌或只有用户快照都视为不可用，会被 `clear()`。
- 旧快照缺 `id` 会被清掉、需要重新登录（`id` 用于判断“这条留言是不是我的”）。
- 缺 `avatar` / `bio` 按空串归一，不踢下线。
- 用户快照只用于展示，身份/权限每次由后端回库判定；快照被篡改最多显示错名字，不会提权。

### 401 处理

请求返回 401 时，前端清本地态并弹回登录框，**草稿保留**。登出是先清本地、再尽力通知后端拉黑令牌；后端 Redis 故障对登出“失败关闭”会回 403，但本地仍应退出，否则用户点退出却一直显示已登录。

## 评论 `CommentList` / `CommentComposer`

- `GET /comments/{path}?p=&size=`，每页 10。接口**不返回总数**，`hasMore` 靠“本页是否拿满 size”推断。
- 发表必须登录（后端 `GetCurrentUser`）。
- 输入是纯文本：`utils/comment.ts` 的 `commentTextToHtml` 先转义 `& < >`，再把换行转 `<br>`，最后以 HTML 提交。**不要把原始输入直接当 HTML 发。**
- `COMMENT_MAX_LENGTH = 2000`，前后端各卡一次。
- **只能回复顶层评论**：后端 `GetList` 只取“父级是顶层评论”的一层回复，回复一条回复能入库但永远不会显示，所以 UI 不提供该入口。
- 发表成功：根评论回第 1 页（新评论倒序）；回复成功原地 `refresh()`。
- 列表内容已由后端 nh3 消毒，用 `v-html` 渲染。

## 留言板 `/guestbook`

- 公开列表 `GET /msg/list`，**分页参数是 `p`，不是 `page`**，每页 10；返回 `{total, items}`。
- 发表 `POST /msg`，body 只允许 `content`；先转义再以 HTML 提交，后端消毒。
- 一人一条；已留过言时编辑区替换为提示。
- 能否删除：`user.is_admin` 或 `item.user_id === user.id`。账号已注销（`user_id` 为 NULL）的留言仅管理员可删。
- 删除走 `DELETE /msg/del?id=`。
- **修改资料也在这里**：点自己的头像（编辑区 / “已留过言”提示 / 自己的留言卡片）打开 `ProfileDialog`。

### `ProfileDialog`

- 调 `PUT /user/profile`，只提交**真正改动过的键**：

```ts
if (username !== original.username) payload.username = username
if (avatar !== original.avatar) payload.avatar = avatar || null
if (bio !== original.bio) payload.bio = bio || null
```

只发全量会把本地旧快照里缺失的 `avatar` / `bio` 一起清空（例如“只改用户名”却把头像和简介清掉）。

- 前端预校验：用户名 2–50 且不含空白；头像 ≤255 且必须是 `http(s)` 链接；简介 ≤200。
- 邮箱只读展示，不可修改。
- 成功后用 `useAuth.applyProfile` 同步内存与 localStorage 快照。
- 历史留言展示的是发表时的昵称/头像快照，不会随资料修改回写。

## 关于页

- 正文来自 `web/app/content/about.md`（代码里写 `~/content/about.md`，`~` 指向 Nuxt `srcDir = app/`），用 `?raw` 导入，构建期固定。
- `utils/markdown.ts` 是极简渲染器：标题 / 段落 / 列表 / 引用 / 代码块 / 粗体 / 行内代码 / 链接，**输出前先 HTML 转义**，链接协议有白名单。
- 没有引入 marked 等 Markdown 依赖。改关于页只需改 md。
- 页头沿用站点背景图与头像。

## 视觉基线

- `app.vue` 固定全屏 `background.jpg` + 三层遮罩；内容卡片用 `border-white/10 bg-white/[0.06] backdrop-blur-2xl` 玻璃拟态。
- 管理端 `ArticlePreview.vue` **刻意复制了这套排版**。改前台详情页样式时同步改它，否则后台预览与线上不一致。
- `SiteHeader` 的“首页 / 文章 / 留言 / 关于”导航用 `useRoute()` 判断高亮（文章详情归在“文章”项下）。

## 欢迎画面 `WelcomeScreen`

- 首次进入的欢迎画面，**不是路由切换动画**，别和页面跳转挂钩。
- 每个浏览器会话一次：sessionStorage 键 `fishmo_welcome_shown`。
- 3500ms 后整体淡出（背景同时轻微放大），0.8s 淡出；点击任意处 / Esc 可跳过。
- 文字错峰淡入是纯 CSS animation，SSR 不渲染。

## 类型契约

`types/blog.ts` 是后端裸 dict 的**前端契约声明**（后端无 `response_model`，不会自动生成类型）。包含 `ArticlePreview` / `ArticleDetail` / `CommentItem` / `AuthUser` / `AuthData` / `RegisterPayload` / `MsgItem` / `Envelope<T>` 等。

改 `app/schemas/*.py` 的返回键名时，必须同步改它，否则类型检查与运行时都会错位。

## 错误文案

`utils/api.ts` 的 `describeError`：

- 业务错误的 `detail` 是字符串 → 直接展示；
- FastAPI 422 的 `detail` 是**数组**，只采纳含中文的 `msg`（去掉 `Value error, ` 前缀），其余落到状态码兜底中文；
- 没有状态码 → “网络连接失败，请检查网络后重试”。

前端预校验规则要与后端 Pydantic 对齐（例如注册密码“≥8 位且含字母数字”在前后端各写了一份）。

## 构建与校验的边界

```bash
cd web && npm run dev        # :3000
cd web && npm run build      # 产物在 web/.output/
cd web && npm run typecheck  # nuxi typecheck（vue-tsc）
```

- **`nuxt build` 不跑类型检查**，只能证明“能构建”。要证明类型正确必须另跑 `npm run typecheck`。
- `nuxi typecheck` 会打印一条 `vue-router/volar/sfc-route-blocks` 未导出的解析告警（vue-router 4.6.4 与 Nuxt 生成的 tsconfig 版本错配），**不影响退出码，别去修依赖**。
- **不要在 dev 服务运行时跑 `npm run build`**：构建与 dev 共用 `node_modules/.cache/nuxt/.nuxt`，构建结束会触发 dev 重启，已打开页面会因旧模块 URL 失效报 `Failed to fetch dynamically imported module`。要验构建先停 dev。

部署与“线上跑的是旧构建”的排查见 [`deploy.md`](deploy.md)。