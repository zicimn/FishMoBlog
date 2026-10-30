<script setup lang="ts">
import { describeError } from '~/composables/useApi'

// 后端 GET /admin/comment/list 的返回（schemas/comment.py 的 to_admin_comment）。
// 列表是扁平结构：顶层评论与回复按时间混排，parent_id 非空表示这是一条回复。
type AdminComment = {
  id: number
  article_id: number
  article_path: string
  article_title: string
  parent_id: number | null
  user_id: number | null
  username: string
  avatar: string
  content: string
  status: number
  created_at: string
}

const api = useApi()
const toast = useToast()
const route = useRoute()
const router = useRouter()

const size = 20
const page = ref(Number(route.query.page) || 1)
const statusFilter = ref<number | null>(route.query.status ? Number(route.query.status) : null)

const items = ref<AdminComment[]>([])
const total = ref(0)
const loading = ref(false)
const errorMsg = ref('')

const pending = ref<AdminComment | null>(null)
const deleting = ref(false)

// 评论状态与文章状态取值不同（0/1/2 vs 1/2/3），不能复用文章页的 StatusBadge。
const STATUS_MAP: Record<number, { label: string; cls: string }> = {
  0: { label: '待审核', cls: 'bg-amber-50 text-amber-700 ring-amber-200' },
  1: { label: '正常', cls: 'bg-emerald-50 text-emerald-700 ring-emerald-200' },
  2: { label: '屏蔽', cls: 'bg-slate-100 text-slate-500 ring-slate-200' },
}

function statusMeta(status: number) {
  return STATUS_MAP[status] ?? { label: `未知(${status})`, cls: 'bg-rose-50 text-rose-700 ring-rose-200' }
}

function fmt(dt: string) {
  if (!dt) return '——'
  const d = new Date(dt)
  return Number.isNaN(d.getTime()) ? dt : d.toLocaleString('zh-CN', { hour12: false })
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const query: Record<string, unknown> = { page: page.value, size }
    if (statusFilter.value !== null) query.status = statusFilter.value

    const data = await api.get<{ total: number; items: AdminComment[] }>('/admin/comment/list', query)
    items.value = data?.items ?? []
    total.value = data?.total ?? 0

    await router.replace({
      query: {
        ...(page.value > 1 ? { page: String(page.value) } : {}),
        ...(statusFilter.value !== null ? { status: String(statusFilter.value) } : {}),
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

watch([page, statusFilter], () => load())

onMounted(load)

async function confirmDelete() {
  const target = pending.value
  if (!target) return
  deleting.value = true
  try {
    await api.del(`/comments/${target.id}`)
    toast.ok('已删除该评论')
    pending.value = null
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
        <h1 class="text-xl font-semibold tracking-tight text-slate-900">评论管理</h1>
        <p class="mt-1 text-sm text-slate-500">
          按时间倒序展示全部评论（含回复与已屏蔽/待审核项），内容已由后端 nh3 白名单消毒。
        </p>
      </div>
    </header>

    <div class="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
      <select
        v-model="statusFilter"
        class="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none
               focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
      >
        <option :value="null">全部状态</option>
        <option :value="1">正常</option>
        <option :value="2">屏蔽</option>
        <option :value="0">待审核</option>
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

    <div class="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 text-xs text-slate-500">
          <tr>
            <th class="px-4 py-3 text-left font-medium">评论内容</th>
            <th class="px-4 py-3 text-left font-medium w-40">作者</th>
            <th class="px-4 py-3 text-left font-medium w-24">状态</th>
            <th class="px-4 py-3 text-left font-medium w-44">时间</th>
            <th class="px-4 py-3 text-right font-medium w-24">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="row in items" :key="row.id" class="hover:bg-slate-50/60 transition-colors align-top">
            <td class="px-4 py-3">
              <p v-if="row.parent_id" class="mb-1 text-[11px] text-slate-400">
                回复 #{row.parent_id}
              </p>
              <!-- content 由后端 sanitize_html 消毒后入库，可用 v-html 渲染 -->
              <div class="line-clamp-3 max-w-xl break-words text-slate-700" v-html="row.content"></div>
              <NuxtLink
                :to="`/articles/${row.article_id}/edit`"
                class="mt-1 inline-block max-w-xl truncate text-xs text-slate-400 hover:text-slate-700"
              >
                《{{ row.article_title || row.article_path }}》
              </NuxtLink>
            </td>
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <img
                  v-if="row.avatar"
                  :src="row.avatar"
                  alt=""
                  class="h-7 w-7 shrink-0 rounded-full object-cover bg-slate-100"
                >
                <span
                  v-else
                  class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs text-slate-500"
                >
                  {{ (row.username || '?').slice(0, 1) }}
                </span>
                <div class="min-w-0">
                  <p class="truncate text-slate-700">{{ row.username }}</p>
                  <p class="text-[11px] text-slate-400">
                    {{ row.user_id ? `用户 #${row.user_id}` : '访客/已删号' }}
                  </p>
                </div>
              </div>
            </td>
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center rounded-full px-2 py-0.5 text-xs ring-1 ring-inset"
                :class="statusMeta(row.status).cls"
              >
                {{ statusMeta(row.status).label }}
              </span>
            </td>
            <td class="px-4 py-3 text-xs text-slate-500">{{ fmt(row.created_at) }}</td>
            <td class="px-4 py-3 text-right whitespace-nowrap">
              <button
                class="text-xs text-rose-600 hover:text-rose-700 underline underline-offset-2"
                @click="pending = row"
              >
                删除
              </button>
            </td>
          </tr>
          <tr v-if="!loading && !items.length">
            <td colspan="5" class="px-4 py-16 text-center text-sm text-slate-400">
              {{ errorMsg ? '加载失败' : '没有符合条件的评论' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AppPagination v-model:page="page" :size="size" :total="total" />

    <!-- 删除确认 -->
    <div v-if="pending" class="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 px-6">
      <div class="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 class="text-base font-semibold text-slate-900">确认删除这条评论？</h2>
        <div class="mt-2 max-h-40 overflow-auto rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600">
          <div class="break-words" v-html="pending.content"></div>
        </div>
        <p class="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700 leading-relaxed">
          后端是硬删除，其下<strong class="font-semibold">所有回复会一并删除</strong>，不可恢复。
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