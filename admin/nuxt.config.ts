import tailwindcss from '@tailwindcss/vite'

// 管理端：只做后台界面，API 全部来自 FastAPI 后端（本仓 app/）。
export default defineNuxtConfig({
  compatibilityDate: '2026-10-26',
  devtools: { enabled: false },

  // 博客前台占 3000，管理端固定 3001：本地同时起两个前端时不会抢端口，
  // 后端 CORS_ORIGINS 需要包含 http://localhost:3001。
  devServer: { port: 3001 },

  modules: ['@pinia/nuxt'],
  css: ['~/assets/css/main.css'],
  vite: { plugins: [tailwindcss()] },

  runtimeConfig: {
    public: {
      // 后端地址，可用 NUXT_PUBLIC_API_BASE 覆盖
      apiBase: 'http://127.0.0.1:8000',
    },
  },

  // 令牌存在 localStorage：SSR 阶段读不到，开了 SSR 只会让首屏闪一下未登录态。
  // 管理端不需要 SEO，直接关掉 SSR 走纯 SPA，路由守卫也只在客户端跑。
  ssr: false,

  app: {
    head: {
      title: '博客管理后台',
      meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1' }],
    },
  },
})