<script setup lang="ts">
import { describeError } from '~/composables/useApi'

type AdminItem = {
  id: number
  title: string
  path: string
  status: number
  category_id: number | null
  views: number
  created_at: string
  updated_at: string
}

const api = useApi()
const toast = useToast()
const route = useRoute()
const router = useRouter()

const size = 20
const page = ref(Number(route.query.page) || 1)
const statusFilter = ref<number | null>(route.query.status ? Number(route.query.status) : null)
const keyword = ref(typeof route.query.keyword === 'string' ? route.query.keyword : '')

const items = ref<AdminItem[]>([])
const total = ref(0)
const loading = ref(false)
const errorMsg = ref('')

// 删除确认：pending 为 null 表示没有待确认的项
const pending = ref<AdminItem | null>(null)
const deleting = ref(false)

// 预览：列表接口（to_admin_preview）**不含 content**，必须按需再打一次详情接口。
// 只在点击时单发一次，不做批量预取，避免列表页 N 次请求把后端打满。
type PreviewDetail = {
  title?: string
  path?: string
  description?: string
  content?: string
  cover?: string | null
  // 预览按前台详情页渲染，style（装饰光晕）与 created_at（发布时间）也要带上
  style?: string | null
  status?: number | null
  category_id?: number | null
  created_at?: string | null
  updated_at?: string | null
  views?: number
}
const previewOpen = ref(false)
const previewLoading = ref(false)
const previewArticle = ref<PreviewDetail | null>(null)
// 连点不同行时丢弃过期响应，避免慢请求把后点的那篇覆盖回前一篇
let previewSeq = 0

async function openPreview(row: AdminItem) {
  previewOpen.value = true
  previewLoading.value = true
  previewArticle.value = null
  const seq = ++previewSeq
  try {
    const detail = await api.get<PreviewDetail>(`/admin/article/${row.id}`)
    if (seq !== previewSeq) return
    previewArticle.value = detail ?? null
  } catch (err) {
    if (seq !== previewSeq) return
    previewOpen.value = false
    toast.err(describeError(err))
  } finally {
    if (seq === previewSeq) previewLoading.value = false
  }
}

function fmt(dt: string) {
  if (!dt) return '——'
  // 后端返回的是 datetime 序列化结果，交给浏览器本地化即可
  const d = new Date(dt)
  return Number.isNaN(d.getTime()) ? dt : d.toLocaleString('zh-CN', { hour12: false })
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const query: Record<string, unknown> = { page: page.value, size }
    if (statusFilter.value) query.status = statusFilter.value
    if (keyword.value.trim()) query.keyword = keyword.value.trim()

    const data = await api.get<{ total: number; items: AdminItem[] }>('/admin/article/list', query)
    items.value = data?.items ?? []
    total.value = data?.total ?? 0

    // 把筛选条件写进 URL：刷新/分享链接后状态还在，浏览器前进后退也能用
    await router.replace({
      query: {
        ...(page.value > 1 ? { page: String(page.value) } : {}),
        ...(statusFilter.value ? { status: String(statusFilter.value) } : {}),
        ...(keyword.value.trim() ? { keyword: keyword.value.trim() } : {}),
      },
    })
  } catch (err) {
    errorMsg.value = describeError(err)
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// 关键词输入防抖：列表接口是打库的，别每敲一个字符打一次
let timer: ReturnType<typeof setTimeout> | undefined
watch(keyword, () => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    page.value = 1
    load()
  }, 350)
})

watch([page, statusFilter], () => load())

onMounted(load)

async function confirmDelete() {
  const target = pending.value
  if (!target) return
  deleting.value = true
  try {
    await api.del(`/admin/article/remove/${target.id}`)
    toast.ok(`已删除《${target.title}》`)
    pending.value = null
    // 删掉当前页最后一条时往前翻一页，避免停在空页
    if (items.value.length === 1 && page.value > 1) page.value -= 1
    else await load()
  } catch (err) {
    toast.err(describeError(err))
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-xl font-semibold tracking-tight text-slate-900">文章管理</h1>
        <p class="mt-1 text-sm text-slate-500">
          后台可见全部状态（正常 / 隐藏 / 草稿），前台只能看到「正常」。
        </p>
      </div>
      <NuxtLink
        to="/articles/new"
        class="shrink-0 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 transition-colors"
      >
        写新文章
      </NuxtLink>
    </header>

    <!-- 筛选 -->
    <div class="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
      <input
        v-model="keyword"
        maxlength="100"
        placeholder="按标题搜索…"
        class="w-64 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none
               focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
      >
      <select
        v-model="statusFilter"
        class="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none
               focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
      >
        <option :value="null">全部状态</option>
        <option :value="1">正常</option>
        <option :value="2">隐藏</option>
        <option :value="3">草稿</option>
      </select>
      <button
        class="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
        @click="load"
      >
        刷新
      </button>
      <span v-if="loading" class="text-xs text-slate-400">加载中…</span>
    </div>

    <p v-if="errorMsg" class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {{ errorMsg }}
    </p>

    <!-- 列表 -->
    <div class="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 text-xs text-slate-500">
          <tr>
            <th class="px-4 py-3 text-left font-medium">标题</th>
            <th class="px-4 py-3 text-left font-medium w-24">状态</th>
            <th class="px-4 py-3 text-left font-medium w-24">分类</th>
            <th class="px-4 py-3 text-right font-medium w-24">浏览量</th>
            <th class="px-4 py-3 text-left font-medium w-44">更新时间</th>
            <th class="px-4 py-3 text-right font-medium w-32">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="row in items" :key="row.id" class="hover:bg-slate-50/60 transition-colors">
            <td class="px-4 py-3">
              <p class="font-medium text-slate-800 truncate max-w-md">{{ row.title }}</p>
              <p class="text-xs text-slate-400 font-mono truncate max-w-md">/article/{{ row.path }}</p>
            </td>
            <td class="px-4 py-3"><StatusBadge :status="row.status" /></td>
            <td class="px-4 py-3 text-xs text-slate-500">
              {{ row.category_id ? `#${row.category_id}` : '未分类' }}
            </td>
            <td class="px-4 py-3 text-right text-slate-600 tabular-nums">{{ row.views }}</td>
            <td class="px-4 py-3 text-xs text-slate-500">{{ fmt(row.updated_at) }}</td>
            <td class="px-4 py-3 text-right whitespace-nowrap">
              <NuxtLink
                :to="`/articles/${row.id}/edit`"
                class="text-xs text-slate-600 hover:text-slate-900 underline underline-offset-2"
              >
                编辑
              </NuxtLink>
              <button
                class="ml-3 text-xs text-slate-600 hover:text-slate-900 underline underline-offset-2"
                @click="openPreview(row)"
              >
                预览
              </button>
              <button
                class="ml-3 text-xs text-rose-600 hover:text-rose-700 underline underline-offset-2"
                @click="pending = row"
              >
                删除
              </button>
            </td>
          </tr>
          <tr v-if="!loading && !items.length">
            <td colspan="6" class="px-4 py-16 text-center text-sm text-slate-400">
              {{ errorMsg ? '加载失败' : '没有符合条件的文章' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AppPagination v-model:page="page" :size="size" :total="total" />

    <!-- 已保存文章预览：点击「预览」时才拉详情（列表接口不含 content） -->
    <ArticlePreview
      :open="previewOpen"
      :loading="previewLoading"
      :article="previewArticle"
      @close="previewOpen = false"
    />

    <!-- 删除确认 -->
    <div v-if="pending" class="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 px-6">
      <div class="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 class="text-base font-semibold text-slate-900">确认删除这篇文章？</h2>
        <p class="mt-2 text-sm text-slate-600">
          《{{ pending.title }}》
        </p>
        <p class="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700 leading-relaxed">
          后端是硬删除，<strong class="font-semibold">不可恢复</strong>；
          该文章下的评论是否级联由数据库外键决定，删前请确认。
        </p>
        <div class="mt-5 flex justify-end gap-3">
          <button
            class="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
            @click="pending = null"
          >
            取消
          </button>
          <button
            :disabled="deleting"
            class="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white
                   hover:bg-rose-700 disabled:opacity-50 transition-colors"
            @click="confirmDelete"
          >
            {{ deleting ? '删除中…' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>