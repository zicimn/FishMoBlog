<script setup lang="ts">
// 文章预览：新建/编辑页（未保存态）与列表页（已保存态）共用同一个弹窗。
//
// 视觉基准是**前台详情页**（web/app/pages/article/[path].vue）：深色背景图、
// 玻璃卡片、封面与正文合成一块、正文排版也与前台一致。预览的意义就是
// 「发出去长什么样」，所以这里刻意复制前台的布局与字号，而不是沿用后台白底简排。
// 改前台详情页样式时，记得同步这里，否则预览会逐渐失真。
//
// 正文按后端存的原始 HTML 直接渲染（v-html）。这是管理端、且文章只有管理员能写，
// 与前台渲染原始 HTML 的既有取向一致；代价是若正文里混入 <img onerror=...>
// 之类的脚本，会在后台域名下执行（可读到 localStorage 里的令牌）。本轮不引入
// 消毒依赖，风险与建议见交付报告。
//
// 预览**不触发任何上传**：未保存的正文里若有 blob: 占位图，直接在同一个浏览器
// 会话里渲染即可；封面也优先用本地 objectURL，而不是等上传后的 Cloudinary 地址。
type PreviewArticle = {
  title?: string
  path?: string
  description?: string
  content?: string
  cover?: string | null
  style?: string | null
  status?: number | null
  category_name?: string | null
  category_id?: number | null
  created_at?: string | null
  updated_at?: string | null
  views?: number
}

const props = withDefaults(
  defineProps<{
    open: boolean
    loading?: boolean
    article?: PreviewArticle | null
  }>(),
  { loading: false, article: null },
)

const emit = defineEmits<{ (e: 'close'): void }>()

function close() {
  emit('close')
}

// Esc 关闭：挂在 window 上而不是弹窗元素上，省得依赖焦点管理。
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.open) close()
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

// 预览是整屏浮层，打开期间锁住底层页面的滚动，避免滚轮滚到后台表单。
watch(
  () => props.open,
  (open) => {
    if (typeof document === 'undefined') return
    document.body.style.overflow = open ? 'hidden' : ''
  },
  { immediate: true },
)
onBeforeUnmount(() => {
  if (typeof document !== 'undefined') document.body.style.overflow = ''
})

// 与前台一致的日期格式（web/app/utils/date.ts）
const dateFormatter = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
})

function formatDate(value?: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : dateFormatter.format(date)
}

const ENTITIES: Record<string, string> = {
  '&amp;': '&',
  '&lt;': '<',
  '&gt;': '>',
  '&quot;': '"',
  '&#39;': "'",
  '&nbsp;': ' ',
}

// 只用于字数统计与目录文字，不追求完整 HTML 解析（同 web/app/utils/content.ts）
function stripHtml(html: string): string {
  return html
    .replace(/<[^>]*>/g, ' ')
    .replace(/&(amp|lt|gt|quot|#39|nbsp);/g, (entity) => ENTITIES[entity] ?? entity)
    .replace(/\s+/g, ' ')
    .trim()
}

type TocItem = { id: string; level: number; text: string }

// 给正文标题补锚点 id 并抽出目录，和前台详情页保持同一套逻辑。
// 这里不做滚动高亮（前台是用 window 上的 IntersectionObserver，预览的滚动容器是弹层），
// 只保证目录能点、能跳。
function buildToc(html: string): { html: string; toc: TocItem[] } {
  const toc: TocItem[] = []
  let index = 0

  const withIds = html.replace(
    /<h([1-4])([^>]*)>([\s\S]*?)<\/h\1>/gi,
    (match: string, level: string, attrs: string, inner: string) => {
      const text = stripHtml(inner)
      if (!text) return match
      const id = `preview-h-${index++}`
      toc.push({ id, level: Number(level), text })
      const cleanAttrs = attrs.replace(/\sid=(["']).*?\1/i, '')
      return `<h${level}${cleanAttrs} id="${id}">${inner}</h${level}>`
    },
  )

  return { html: withIds, toc }
}

const rendered = computed(() => buildToc(props.article?.content ?? ''))
const toc = computed(() => rendered.value.toc)

const charCount = computed(() =>
  stripHtml(props.article?.content ?? '').replace(/\s/g, '').length,
)

const initial = computed(() => props.article?.title?.trim().charAt(0) || '文')

const publishedLabel = computed(() =>
  formatDate(props.article?.created_at ?? props.article?.updated_at),
)
const updatedLabel = computed(() => formatDate(props.article?.updated_at))

// 文案与 StatusBadge 保持一致，只是换成深色底上的配色（预览是深色主题）
const STATUS_META: Record<number, { label: string; cls: string }> = {
  1: { label: '正常', cls: 'bg-emerald-400/15 text-emerald-200 ring-emerald-300/25' },
  2: { label: '隐藏', cls: 'bg-amber-400/15 text-amber-200 ring-amber-300/25' },
  3: { label: '草稿', cls: 'bg-white/10 text-white/70 ring-white/15' },
}
const statusMeta = computed(
  () =>
    STATUS_META[props.article?.status ?? 3] ?? {
      label: `未知(${props.article?.status})`,
      cls: 'bg-rose-400/15 text-rose-200 ring-rose-300/25',
    },
)
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      role="dialog"
      aria-modal="true"
      aria-label="文章预览"
      class="fixed inset-0 z-50 overflow-y-auto overscroll-contain bg-slate-950 text-white"
    >
      <!--
        与前台 app.vue 同一套背景：public/background.jpg + 三层遮罩。
        玻璃卡片需要「背后有东西可透」，所以背景图固定铺满整屏。
      -->
      <div class="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
        <img src="/background.jpg" alt="" class="h-full w-full scale-105 object-cover">
        <div class="absolute inset-0 bg-slate-950/60" />
        <div
          class="absolute inset-0 bg-[radial-gradient(120%_80%_at_50%_-10%,rgba(56,189,248,0.18),transparent_55%)]"
        />
        <div class="absolute inset-0 bg-gradient-to-b from-slate-950/10 via-transparent to-slate-950/80" />
      </div>

      <!-- 浮动控制条：预览态不属于站点本身，所以不放进正文卡片里 -->
      <div class="pointer-events-none sticky top-0 z-20 flex items-start justify-between gap-4 px-4 py-3">
        <div
          class="pointer-events-auto max-w-[22rem] rounded-2xl border border-white/10 bg-white/[0.06] px-3 py-2 backdrop-blur-2xl"
        >
          <div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px]">
            <span class="rounded-full px-2 py-0.5 ring-1 ring-inset" :class="statusMeta.cls">
              {{ statusMeta.label }}
            </span>
            <span v-if="article?.category_name" class="text-white/45">{{ article.category_name }}</span>
            <span v-else-if="article?.category_id" class="text-white/45">分类 #{{ article.category_id }}</span>
            <span v-if="article?.path" class="font-mono text-white/35">/article/{{ article.path }}</span>
          </div>
          <p class="mt-1 text-[10px] leading-relaxed text-white/35">
            预览不保存、不上传；未上传的图片是本会话的本地临时地址
          </p>
        </div>

        <button
          type="button"
          class="pointer-events-auto shrink-0 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs text-white/80 backdrop-blur-xl transition hover:bg-white/15 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
          @click="close"
        >
          关闭预览 <kbd class="ml-1 text-[10px] text-white/40">Esc</kbd>
        </button>
      </div>

      <main class="mx-auto w-full max-w-[1373px] px-5 pb-20 sm:px-8">
        <!-- 加载中 -->
        <div v-if="loading" class="mx-auto mt-8 max-w-3xl animate-pulse" aria-hidden="true">
          <div class="h-80 rounded-3xl border border-white/10 bg-white/[0.05] backdrop-blur-2xl" />
          <div class="mt-6 h-96 rounded-3xl border border-white/10 bg-white/[0.04] backdrop-blur-2xl" />
        </div>

        <template v-else-if="article">
          <!--
            三栏对称栅格：左右各 220px 留白，正文落在中间一列 —— 与前台详情页同款，
            保证预览里的封面/正文宽度和真站一致。窄屏退化成单列。
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
                class="preview-card overflow-hidden rounded-3xl border border-white/10 bg-white/[0.06] shadow-[0_12px_40px_-16px_rgba(2,6,23,0.9)] backdrop-blur-2xl"
              >
                <div class="relative h-[247px] sm:h-[327px]">
                  <img
                    v-if="article.cover"
                    :src="article.cover"
                    :alt="article.title"
                    class="absolute inset-0 h-full w-full object-cover"
                  >
                  <div
                    v-else
                    class="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-sky-500/35 via-indigo-500/25 to-fuchsia-500/35"
                    aria-hidden="true"
                  >
                    <span class="text-[7rem] font-semibold text-white/20">{{ initial }}</span>
                  </div>

                  <!-- 只留一点底部压暗，让图片与下方卡片自然收边 -->
                  <div class="absolute inset-0 bg-gradient-to-t from-slate-950/50 via-transparent to-transparent" />

                  <!-- style 是后台设定的文章背景色（CSS 颜色值），这里当前台的装饰光晕用 -->
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
                    <time v-if="publishedLabel" :datetime="article.created_at ?? article.updated_at ?? undefined">
                      {{ publishedLabel }}
                    </time>
                    <span v-if="publishedLabel" class="h-0.5 w-0.5 rounded-full bg-white/30" />
                    <span>{{ charCount }} 字</span>
                    <template v-if="typeof article.views === 'number'">
                      <span class="h-0.5 w-0.5 rounded-full bg-white/30" />
                      <span>{{ article.views }} 次浏览</span>
                    </template>
                  </div>

                  <h1 class="mt-4 max-w-3xl text-3xl font-semibold leading-tight tracking-tight text-white sm:text-5xl">
                    {{ article.title?.trim() || '（未填写标题）' }}
                  </h1>

                  <p
                    v-if="article.description"
                    class="mt-4 max-w-2xl text-sm leading-relaxed text-white/55 sm:text-base"
                  >
                    {{ article.description }}
                  </p>
                  <p v-else class="mt-4 text-sm italic text-white/25">（未填写摘要）</p>
                </header>

                <!-- 标题区与正文之间的透明玻璃分割线 -->
                <div
                  class="relative h-px w-full bg-gradient-to-r from-transparent via-white/30 to-transparent shadow-[0_0_18px_rgba(148,197,255,0.25)]"
                  aria-hidden="true"
                />

                <!-- 正文：后端存的就是 HTML，这里直出（风险说明见 script 顶部） -->
                <section class="bg-slate-950/20 p-6 sm:p-10">
                  <div v-if="article.content" class="preview-content" v-html="rendered.html" />
                  <p v-else class="text-sm italic text-white/25">（正文为空）</p>
                </section>
              </article>

              <div
                v-if="updatedLabel"
                class="mt-8 flex items-center justify-between border-t border-white/5 pt-6 text-[11px] text-white/35"
              >
                <span>最后更新：{{ updatedLabel }}</span>
                <span>预览模式</span>
              </div>
            </div>

            <!-- 桌面侧边目录（与前台详情页同款位置） -->
            <aside v-if="toc.length" class="sticky top-24 hidden xl:col-start-3 xl:block">
              <div class="rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-2xl">
                <p class="text-[10px] uppercase tracking-[0.25em] text-white/35">目录</p>
                <nav class="mt-3 max-h-[60vh] space-y-0.5 overflow-y-auto pr-1">
                  <a
                    v-for="item in toc"
                    :key="item.id"
                    :href="`#${item.id}`"
                    class="block truncate rounded-lg py-1 pr-2 text-xs leading-relaxed text-white/45 transition hover:bg-white/[0.06] hover:text-white/75"
                    :style="{ paddingLeft: `${6 + (item.level - 1) * 10}px` }"
                  >
                    {{ item.text }}
                  </a>
                </nav>
              </div>
            </aside>
          </div>
        </template>

        <div v-else class="mt-8 rounded-3xl border border-white/10 bg-white/[0.06] px-6 py-16 text-center text-sm text-white/50 backdrop-blur-2xl">
          没有可预览的内容。
        </div>
      </main>
    </div>
  </Teleport>
</template>

<style scoped>
/* v-html 生成的节点没有 scoped 属性，必须用 :deep() 才能命中。
   排版值逐条对齐 web/app/assets/css/main.css 的 .article-content。 */
.preview-content {
  font-size: 0.9375rem;
  line-height: 1.9;
  color: rgb(255 255 255 / 0.75);
  overflow-wrap: anywhere;
}

.preview-content :deep(> * + *) {
  margin-top: 1.15em;
}

.preview-content :deep(h1),
.preview-content :deep(h2),
.preview-content :deep(h3),
.preview-content :deep(h4) {
  color: #fff;
  font-weight: 600;
  line-height: 1.35;
  margin-top: 1.8em;
  /* 目录跳转时留出顶部空间，避免标题贴在浮层控制条下面 */
  scroll-margin-top: 6rem;
}

.preview-content :deep(h1) { font-size: 1.75rem; }
.preview-content :deep(h2) { font-size: 1.4rem; }
.preview-content :deep(h3) { font-size: 1.15rem; }

.preview-content :deep(a) {
  color: rgb(125 211 252);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.preview-content :deep(strong) {
  color: #fff;
  font-weight: 600;
}

.preview-content :deep(img) {
  display: block;
  max-width: 100%;
  height: auto;
  margin: 1.5rem auto;
  border-radius: 1rem;
  border: 1px solid rgb(255 255 255 / 0.1);
}

.preview-content :deep(ul),
.preview-content :deep(ol) {
  padding-left: 1.5rem;
}

.preview-content :deep(ul) { list-style: disc; }
.preview-content :deep(ol) { list-style: decimal; }
.preview-content :deep(li + li) { margin-top: 0.35rem; }

.preview-content :deep(blockquote) {
  border-left: 2px solid rgb(125 211 252 / 0.5);
  padding-left: 1rem;
  color: rgb(255 255 255 / 0.55);
}

.preview-content :deep(code) {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  font-size: 0.875em;
  background: rgb(2 6 23 / 0.6);
  padding: 0.15em 0.4em;
  border-radius: 0.35rem;
}

.preview-content :deep(pre) {
  background: rgb(2 6 23 / 0.75);
  border: 1px solid rgb(255 255 255 / 0.08);
  border-radius: 1rem;
  padding: 1rem 1.25rem;
  overflow-x: auto;
}

.preview-content :deep(pre code) {
  background: transparent;
  padding: 0;
  font-size: 0.85rem;
}

.preview-content :deep(hr) {
  border-color: rgb(255 255 255 / 0.1);
  margin: 2rem 0;
}

.preview-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.preview-content :deep(th),
.preview-content :deep(td) {
  border: 1px solid rgb(255 255 255 / 0.1);
  padding: 0.5rem 0.75rem;
  text-align: left;
}

.preview-content :deep(th) {
  background: rgb(255 255 255 / 0.05);
  color: #fff;
}

/* 与前台 .animate-rise 同节奏的入场 */
@keyframes preview-rise {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.preview-card {
  animation: preview-rise 0.7s cubic-bezier(0.22, 0.68, 0.32, 1) both;
}

@media (prefers-reduced-motion: reduce) {
  .preview-card {
    animation: none;
  }
}
</style>