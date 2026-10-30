<script setup lang="ts">
import aboutSource from '~/content/about.md?raw'
import { renderMarkdown } from '~/utils/markdown'

// 正文是仓库内的 about.md：?raw 拿到原始文本，再用本地极简渲染器转成 HTML。
// 内容在构建期就固定了，不需要响应式。
const html = renderMarkdown(aboutSource)

useHead({
  title: '关于 · Fishmo',
  meta: [
    {
      name: 'description',
      content: '关于 Fishmo 与这个博客：技术、生活，以及一些还没想清楚的事。',
    },
  ],
})
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <SiteHeader subtitle="关于" />

    <main class="mx-auto w-full max-w-4xl flex-1 px-5 pb-20 sm:px-8">
      <article
        class="animate-rise mt-8 overflow-hidden rounded-3xl border border-white/10 bg-white/[0.06] shadow-[0_12px_40px_-16px_rgba(2,6,23,0.9)] backdrop-blur-2xl"
      >
        <!-- 封面：沿用站点背景图，压一层由下往上的暗色让头像自然过渡 -->
        <div class="relative h-40 sm:h-64">
          <img
            src="/background.jpg"
            alt=""
            class="absolute inset-0 h-full w-full object-cover opacity-90"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-slate-950/25 to-transparent" />
        </div>

        <div class="relative px-6 pb-10 sm:px-10 sm:pb-14">
          <img
            src="/ico.jpg"
            alt="Fishmo 的头像"
            class="-mt-12 h-24 w-24 rounded-full object-cover ring-4 ring-slate-950/80 sm:-mt-16 sm:h-32 sm:w-32"
          />

          <header class="mt-5 border-b border-white/10 pb-6 sm:mt-6 sm:pb-8">
            <h1 class="text-2xl font-semibold tracking-tight text-white sm:text-4xl">关于我</h1>
            <p class="mt-2 text-[11px] uppercase tracking-[0.3em] text-sky-300/60 sm:text-xs">
              Hello World, I'm Fishmo
            </p>
          </header>

          <!-- 正文样式复用文章页的 .article-content（main.css） -->
          <div class="article-content mt-6" v-html="html" />
        </div>
      </article>
    </main>

    <SiteFooter />
  </div>
</template>