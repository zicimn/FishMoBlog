<script setup lang="ts">
import type { ArticleListData, Envelope } from '~/types/blog'

const apiBase = useApiBase()
const apiBaseLabel = useApiBaseLabel()

const page = ref(1)
const size = 12

// GET /article/ 返回 { msg, code, data: { total, items } }，与首页同一接口，
// 只是每页条数多三篇（12 = 3 列 × 4 行）。
const { data, pending, error, refresh } = await useFetch<Envelope<ArticleListData>>('/article/', {
  baseURL: apiBase,
  query: { page, size },
  watch: [page],
})

const items = computed(() => data.value?.data?.items ?? [])
const total = computed(() => data.value?.data?.total ?? 0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / size)))

// 首屏加载（还没有任何数据）才铺骨架屏；翻页时保留旧列表避免闪烁
const showSkeleton = computed(() => pending.value && items.value.length === 0)

useHead(() => ({
  title: '文章 · Fishmo',
  meta: [{ name: 'description', content: 'Fishmo 的全部文章列表。' }],
}))

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
    <SiteHeader subtitle="文章" />

    <main class="mx-auto w-full max-w-6xl flex-1 px-5 pb-20 sm:px-8">
      <header class="animate-rise pt-10 sm:pt-14">
        <p class="text-[10px] uppercase tracking-[0.35em] text-white/30">Archive</p>
        <div class="mt-2 flex flex-wrap items-end justify-between gap-3">
          <h1 class="text-3xl font-semibold tracking-tight text-white sm:text-4xl">全部文章</h1>
          <span class="pb-1 text-[11px] tabular-nums text-white/30">
            {{ totalPages > 1 ? `第 ${page} / ${totalPages} 页 · 共 ${total} 篇` : `共 ${total} 篇` }}
          </span>
        </div>
      </header>

      <!-- 后端不可用 -->
      <section
        v-if="error && items.length === 0"
        class="animate-rise mx-auto mt-10 max-w-xl rounded-3xl border border-rose-300/20 bg-rose-500/10 px-6 py-10 text-center backdrop-blur-2xl"
      >
        <p class="text-sm font-medium text-rose-100/90">暂时读不到文章</p>
        <p class="mt-2 text-xs leading-relaxed text-rose-100/50">
          请确认后端已启动（{{ apiBaseLabel }}），然后重试。
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
      <div
        v-else-if="showSkeleton"
        class="mt-10 grid justify-items-center gap-6 sm:grid-cols-2 lg:grid-cols-3"
        aria-hidden="true"
      >
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
        class="animate-rise mx-auto mt-10 max-w-xl rounded-3xl border border-white/10 bg-white/[0.06] px-6 py-16 text-center backdrop-blur-2xl"
      >
        <p class="text-sm text-white/60">还没有文章</p>
        <NuxtLink to="/" class="mt-4 inline-block text-xs text-sky-200/70 transition hover:text-white">
          回首页看看
        </NuxtLink>
      </section>

      <!-- 文章卡片 -->
      <section v-else class="mt-10 grid justify-items-center gap-6 sm:grid-cols-2 lg:grid-cols-3">
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