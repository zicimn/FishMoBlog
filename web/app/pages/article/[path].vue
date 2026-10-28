<script setup lang="ts">
import type { ArticleDetail, Envelope } from '~/types/blog'
import { buildToc, stripHtml } from '~/utils/content'

const route = useRoute()
const config = useRuntimeConfig()

const path = computed(() => String(route.params.path ?? ''))

// GET /article/{path}：命中即计一次浏览量（后端 GetSlug 内会 incr），
// 返回 { msg, code, data: { ...to_detail } }，to_detail 现已带 cover。
const { data, pending, error, refresh } = await useFetch<Envelope<ArticleDetail>>(
  () => `/article/${encodeURIComponent(path.value)}`,
  { baseURL: config.public.apiBase, watch: [path] },
)

const article = computed(() => data.value?.data ?? null)
const rendered = computed(() => buildToc(article.value?.content ?? ''))
const toc = computed(() => rendered.value.toc)

const plainText = computed(() => stripHtml(article.value?.content ?? ''))
const charCount = computed(() => plainText.value.replace(/\s/g, '').length)

const initial = computed(() => article.value?.title.trim().charAt(0) || '文')

// 后端 HTTPException 的 detail 是字符串（404 表示该 path 不存在）
const is404 = computed(
  () => (error.value as { statusCode?: number } | null)?.statusCode === 404,
)

// 文章不存在时让 SSR 响应真正的 404，而不是 200 + 友好提示（对 SEO 有意义）。
// 客户端导航没有新文档，event 为 undefined，这里自然跳过。
const requestEvent = useRequestEvent()
if (requestEvent && is404.value) {
  setResponseStatus(requestEvent, 404)
}

useHead(() => ({
  title: article.value ? `${article.value.title} · Fishmo` : '文章 · Fishmo',
  meta: [{ name: 'description', content: article.value?.description ?? '' }],
}))

// —— 阅读进度 + 目录滚动高亮 ——
const activeId = ref('')
const readProgress = ref(0)
let observer: IntersectionObserver | null = null

function disconnectObserver() {
  observer?.disconnect()
  observer = null
}

function setupObserver() {
  disconnectObserver()
  if (!import.meta.client || !toc.value.length) return

  observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
      if (visible[0]) activeId.value = visible[0].target.id
    },
    { rootMargin: '-96px 0px -70% 0px', threshold: 0 },
  )

  for (const item of toc.value) {
    const el = document.getElementById(item.id)
    if (el) observer.observe(el)
  }
}

function updateProgress() {
  if (!import.meta.client) return
  const doc = document.documentElement
  const max = doc.scrollHeight - doc.clientHeight
  readProgress.value = max > 0 ? Math.min(100, Math.max(0, (doc.scrollTop / max) * 100)) : 0
}

function handleScroll() {
  updateProgress()
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll, { passive: true })
  window.addEventListener('resize', updateProgress)
  updateProgress()
  setupObserver()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll)
  window.removeEventListener('resize', updateProgress)
  disconnectObserver()
})

// 站内切换到另一篇详情时组件会被复用，观察器要跟着重建
watch(
  () => article.value?.id,
  async () => {
    activeId.value = toc.value[0]?.id ?? ''
    await nextTick()
    setupObserver()
    updateProgress()
  },
  { immediate: true },
)
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <SiteHeader subtitle="文章" />

    <!-- 阅读进度：固定在视口顶端 -->
    <div class="fixed inset-x-0 top-0 z-50 h-0.5 bg-white/5" aria-hidden="true">
      <div
        class="h-full bg-gradient-to-r from-sky-400/80 to-fuchsia-400/80 transition-[width] duration-150"
        :style="{ width: `${readProgress}%` }"
      />
    </div>

    <!-- 容器比列表页的 max-w-6xl 多 221px：左右留白固定，多出的宽度全部给中间正文列 -->
    <main class="mx-auto w-full max-w-[1373px] flex-1 px-5 pb-20 sm:px-8">
      <div class="flex justify-center pt-8">
        <NuxtLink
          to="/"
          class="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.06] px-4 py-2 text-xs text-white/60 backdrop-blur-xl transition hover:bg-white/[0.12] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
        >
          <span aria-hidden="true">←</span>
          返回首页
        </NuxtLink>
      </div>

      <!-- 加载中 -->
      <div v-if="pending && !article" class="mx-auto mt-8 max-w-3xl animate-pulse" aria-hidden="true">
        <div class="h-80 rounded-3xl border border-white/10 bg-white/[0.05] backdrop-blur-2xl" />
        <div class="mt-6 h-96 rounded-3xl border border-white/10 bg-white/[0.04] backdrop-blur-2xl" />
      </div>

      <!-- 读不到 -->
      <section
        v-else-if="error && !article"
        class="animate-rise mx-auto mt-8 max-w-xl rounded-3xl border border-white/10 bg-white/[0.06] px-6 py-16 text-center backdrop-blur-2xl"
      >
        <p class="text-sm text-white/70">
          {{ is404 ? '这篇文章不存在' : '暂时读不到这篇文章' }}
        </p>
        <p class="mt-2 text-xs text-white/40">
          {{
            is404
              ? '它可能已被删除，或还没有对外公开。'
              : `请确认后端已启动（${config.public.apiBase}）。`
          }}
        </p>
        <div class="mt-6 flex items-center justify-center gap-3">
          <button
            type="button"
            class="rounded-full border border-white/15 bg-white/10 px-5 py-2 text-xs font-medium text-white/80 transition hover:bg-white/15 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
            @click="refresh()"
          >
            重试
          </button>
          <NuxtLink
            to="/"
            class="rounded-full border border-white/10 px-5 py-2 text-xs text-white/60 transition hover:bg-white/[0.08] hover:text-white"
          >
            返回首页
          </NuxtLink>
        </div>
      </section>

      <template v-else-if="article">
        <!--
          三栏对称栅格：左右各 220px 留白，正文落在中间一列。
          这样封面与正文天然同宽，且整块内容在页面上居中；
          右侧留白列放目录。窄屏退化成单列。
        -->
        <div class="mt-6 xl:grid xl:grid-cols-[14rem_minmax(0,1fr)_14rem] xl:items-start xl:gap-6">
          <div class="min-w-0 xl:col-start-2">
            <!-- 移动端目录 -->
            <details
              v-if="toc.length"
              class="mb-4 rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-2xl xl:hidden"
            >
              <summary class="cursor-pointer text-xs font-medium text-white/70">
                目录（{{ toc.length }}）
              </summary>
              <nav class="mt-3 flex flex-col gap-0.5">
                <a
                  v-for="item in toc"
                  :key="item.id"
                  :href="`#${item.id}`"
                  class="rounded-lg py-1 pr-2 text-xs text-white/50 transition hover:bg-white/10 hover:text-white"
                  :style="{ paddingLeft: `${8 + (item.level - 1) * 12}px` }"
                >
                  {{ item.text }}
                </a>
              </nav>
            </details>

            <!-- 封面与正文合成一块：中间用透明玻璃缝分隔，不留空隙 -->
            <article
              class="animate-rise overflow-hidden rounded-3xl border border-white/10 bg-white/[0.06] shadow-[0_12px_40px_-16px_rgba(2,6,23,0.9)] backdrop-blur-2xl"
            >
              <div class="relative h-[247px] sm:h-[327px]">
                <img
                  v-if="article.cover"
                  :src="article.cover"
                  :alt="article.title"
                  class="absolute inset-0 h-full w-full object-cover"
                />
                <div
                  v-else
                  class="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-sky-500/35 via-indigo-500/25 to-fuchsia-500/35"
                  aria-hidden="true"
                >
                  <span class="text-[7rem] font-semibold text-white/20">{{ initial }}</span>
                </div>

                <!-- 只留一点底部压暗，让图片与下方卡片自然收边 -->
                <div class="absolute inset-0 bg-gradient-to-t from-slate-950/50 via-transparent to-transparent" />

                <!-- style 是后台设定的文章背景色（CSS 颜色值），这里当装饰光晕用 -->
                <div
                  v-if="article.style"
                  class="pointer-events-none absolute -right-16 -top-20 h-56 w-56 rounded-full opacity-30 blur-3xl"
                  :style="{ backgroundColor: article.style }"
                  aria-hidden="true"
                />
              </div>

              <!-- 标题区与正文在同一个卡片里，但不压在封面上 -->
              <header class="p-6 sm:p-10">
                <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] uppercase tracking-wider text-white/45">
                  <time :datetime="article.created_at">{{ formatDate(article.created_at) }}</time>
                  <span class="h-0.5 w-0.5 rounded-full bg-white/30" />
                  <span>{{ charCount }} 字</span>
                  <span class="h-0.5 w-0.5 rounded-full bg-white/30" />
                  <span>{{ article.views }} 次浏览</span>
                </div>

                <h1 class="mt-4 max-w-3xl text-3xl font-semibold leading-tight tracking-tight text-white sm:text-5xl">
                  {{ article.title }}
                </h1>

                <p
                  v-if="article.description"
                  class="mt-4 max-w-2xl text-sm leading-relaxed text-white/55 sm:text-base"
                >
                  {{ article.description }}
                </p>
              </header>

              <!-- 标题区与正文之间的透明玻璃分割线 -->
              <div
                class="relative h-px w-full bg-gradient-to-r from-transparent via-white/30 to-transparent shadow-[0_0_18px_rgba(148,197,255,0.25)]"
                aria-hidden="true"
              />

              <!--
                正文是后台编辑器保存的原始 HTML：后端只对评论做 nh3 消毒，文章不消毒。
                写入端仅管理员可用，这里按可信内容渲染；若日后开放投稿，
                必须在写入或渲染前补白名单消毒。
              -->
              <section class="bg-slate-950/20 p-6 sm:p-10">
                <div id="article-content" class="article-content" v-html="rendered.html" />
              </section>
            </article>

            <div class="mt-8 flex items-center justify-between border-t border-white/5 pt-6 text-[11px] text-white/35">
              <span>最后更新：{{ formatDate(article.updated_at) }}</span>
              <NuxtLink to="/" class="transition hover:text-white/70">返回首页</NuxtLink>
            </div>

            <!-- 评论：列表公开可读；发表需登录（登录/注册由 CommentComposer 内的弹窗处理） -->
            <CommentList :path="article.path" />
          </div>

          <!-- 桌面侧边目录（参考 Mizuki 的 SidebarTOC） -->
          <aside v-if="toc.length" class="sticky top-8 hidden xl:col-start-3 xl:block">
            <div class="rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-2xl">
              <p class="text-[10px] uppercase tracking-[0.25em] text-white/35">目录</p>
              <nav class="mt-3 max-h-[60vh] space-y-0.5 overflow-y-auto pr-1">
                <a
                  v-for="item in toc"
                  :key="item.id"
                  :href="`#${item.id}`"
                  class="block truncate rounded-lg py-1 pr-2 text-xs leading-relaxed transition"
                  :class="
                    item.id === activeId
                      ? 'bg-white/10 text-white'
                      : 'text-white/45 hover:bg-white/[0.06] hover:text-white/75'
                  "
                  :style="{ paddingLeft: `${6 + (item.level - 1) * 10}px` }"
                >
                  {{ item.text }}
                </a>
              </nav>
            </div>
          </aside>
        </div>
      </template>
    </main>

    <SiteFooter />
  </div>
</template>