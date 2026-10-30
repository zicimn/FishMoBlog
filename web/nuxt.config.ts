import tailwindcss from '@tailwindcss/vite'

// 两种后端地址（为什么 SSR 与浏览器要分开，见 app/composables/useApiBase.ts）：
// - 本地 / 测试：直连 FastAPI；dev 与 typecheck 都走这一套；
// - 生产：浏览器走 nginx 同源的 /api，SSR 仍直连后端。
// 注意 /api 只是浏览器侧的约定：nginx 必须把 /api/ 代理到后端根
// （`location /api/ { proxy_pass http://127.0.0.1:8000/; }`，末尾的斜杠负责剥掉前缀）。
const API_BASE_LOCAL = 'http://127.0.0.1:8000'
const API_BASE_NGINX = '/api'

// 博客前台：只做展示，数据全部来自 FastAPI 后端（本仓 app/）。
// 与 admin/ 的区别：前台要 SEO，所以保留 SSR；admin 是纯 SPA。
export default defineNuxtConfig({
  compatibilityDate: '2026-10-26',
  devtools: { enabled: false },

  // 博客前台占 3000（后端 CORS_ORIGINS 默认就包含这个源），管理端固定 3001。
  devServer: { port: 3000 },

  css: ['~/assets/css/main.css'],
  vite: { plugins: [tailwindcss()] },

  runtimeConfig: {
    // 服务端专用（不会序列化到浏览器）：SSR 直连 FastAPI，不暴露内网地址。
    apiBaseServer: API_BASE_LOCAL,
    public: {
      // 浏览器端实际请求地址，默认本地测试值，生产由下面的 $production 覆盖。
      apiBase: API_BASE_LOCAL,
    },
  },

  // 生产（nuxt build / preview）自动改用 nginx 同源的 /api。
  // 用 Nuxt 的 $production 覆盖而不是读 process.env：项目没装 @types/node，
  // 在 nuxt.config.ts 里用 process 会让 nuxi typecheck 报 TS2591。
  // 部署时仍可用环境变量在运行时覆盖：
  //   NUXT_PUBLIC_API_BASE（浏览器侧）、NUXT_API_BASE_SERVER（SSR 侧，
  //   后端不在同一台机器或端口不同时用）。
  $production: {
    runtimeConfig: {
      apiBaseServer: API_BASE_LOCAL,
      public: { apiBase: API_BASE_NGINX },
    },
  },

  app: {
    head: {
      title: 'Fishmo · 博客',
      htmlAttrs: { lang: 'zh-CN' },
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: '技术、生活，以及一些还没想清楚的事。' },
        { name: 'theme-color', content: '#020617' },
      ],
      link: [{ rel: 'icon', type: 'image/jpeg', href: '/ico.jpg' }],
    },
  },
})