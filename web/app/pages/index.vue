<script setup lang="ts">
import type { ArticleListData, Envelope } from '~/types/blog'

const config = useRuntimeConfig()

const page = ref(1)
const size = 9

// 后端 GET /article/ 返回 { msg, code, data: { total, items } }。
// 用 useFetch 自带 SSR + 响应式 query：page 变化会自动重新请求。
const { data, pending, error, refresh } = await useFetch<Envelope<ArticleListData>>('/article/', {
  baseURL: config.public.apiBase,
  query: { page, size },
  watch: [page],
})

const items = computed(() => data.value?.data?.items ?? [])
const total = computed(() => data.value?.data?.total ?? 0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / size)))

// 首屏加载（还没有任何数据）才铺骨架屏；翻页时保留旧列表避免闪烁
const showSkeleton = computed(() => pending.value && items.value.length === 0)

function goTo(target: number) {
  const next = Math.min(Math.max(1, target), totalPages.value)
  if (next === page.value) return
  page.value = next
  if (import.meta.client) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <SiteHeader />

    <main class="mx-auto w-full max-w-6xl flex-1 px-5 pb-20 sm:px-8">
      <section class="py-16 text-center sm:py-24">
        <p class="text-[11px] tracking-[0.35em] text-sky-200/60">JOURNAL</p>
        <h1 class="mt-5 text-4xl font-semibold tracking-tight text-white sm:text-6xl">
          写点东西，留给时间
        </h1>
        <p class="mx-auto mt-5 max-w-lg text-sm leading-relaxed text-white/50 sm:text-base">
          技术、生活，以及一些还没想清楚的事。每一篇都是一块被时间打磨过的玻璃。
        </p>
        <div class="mt-8 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-4 py-1.5 text-xs text-white/50 backdrop-blur-xl">
          <span class="h-1.5 w-1.5 rounded-full bg-emerald-400/80" />
          共 {{ total }} 篇文章
        </div>
      </section>

      <!-- 后端不可用 -->
      <section
        v-if="error && items.length === 0"
        class="animate-rise mx-auto max-w-xl rounded-3xl border border-rose-300/20 bg-rose-500/10 px-6 py-10 text-center backdrop-blur-2xl"
      >
        <p class="text-sm font-medium text-rose-100/90">暂时读不到文章</p>
        <p class="mt-2 text-xs leading-relaxed text-rose-100/50">
          请确认后端已启动（{{ config.public.apiBase }}），然后重试。
        </p>
        <button
          type="button"
          class="mt-6 rounded-full border border-white/15 bg-white/10 px-5 py-2 text-xs font-medium text-white/80 transition hover:bg-white/15 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
          @click="refresh()"
        >
          重试
        </button>
      </section>

      <!-- 首屏骨架 -->
      <div v-else-if="showSkeleton" class="grid justify-items-center gap-6 sm:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
        <div
          v-for="n in size"
          :key="n"
          class="h-[215px] w-full max-w-[345px] animate-pulse overflow-hidden rounded-3xl border border-white/10 bg-white/[0.05] p-6 backdrop-blur-2xl"
        >
          <div class="mt-auto space-y-3">
            <div class="h-4 w-5/6 rounded bg-white/10" />
            <div class="h-3 w-full rounded bg-white/5" />
            <div class="h-3 w-2/3 rounded bg-white/5" />
          </div>
        </div>
      </div>

      <!-- 空态 -->
      <section
        v-else-if="items.length === 0"
        class="animate-rise mx-auto max-w-xl rounded-3xl border border-white/10 bg-white/[0.06] px-6 py-16 text-center backdrop-blur-2xl"
      >
        <p class="text-sm text-white/60">还没有文章</p>
        <p class="mt-2 text-xs text-white/35">去管理端写第一篇吧。</p>
      </section>

      <!-- 文章卡片 -->
      <section v-else class="grid justify-items-center gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <ArticleCard
          v-for="(article, index) in items"
          :key="article.id"
          :article="article"
          :index="index"
        />
      </section>

      <nav
        v-if="totalPages > 1"
        class="mt-14 flex items-center justify-center gap-2"
        aria-label="分页"
      >
        <button
          type="button"
          :disabled="page <= 1"
          class="rounded-full border border-white/10 bg-white/[0.06] px-5 py-2 text-xs text-white/70 backdrop-blur-xl transition hover:bg-white/[0.12] hover:text-white disabled:cursor-not-allowed disabled:opacity-30 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
          @click="goTo(page - 1)"
        >
          上一页
        </button>
        <span class="min-w-20 text-center text-xs tabular-nums text-white/40">
          {{ page }} / {{ totalPages }}
        </span>
        <button
          type="button"
          :disabled="page >= totalPages"
          class="rounded-full border border-white/10 bg-white/[0.06] px-5 py-2 text-xs text-white/70 backdrop-blur-xl transition hover:bg-white/[0.12] hover:text-white disabled:cursor-not-allowed disabled:opacity-30 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
          @click="goTo(page + 1)"
        >
          下一页
        </button>
      </nav>
    </main>

    <SiteFooter />
  </div>
</template>