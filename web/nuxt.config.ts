import tailwindcss from '@tailwindcss/vite'

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
    public: {
      // 后端地址，可用 NUXT_PUBLIC_API_BASE 覆盖
      apiBase: 'http://127.0.0.1:8000',
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