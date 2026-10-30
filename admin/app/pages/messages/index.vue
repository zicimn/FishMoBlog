<script setup lang="ts">
import { describeError } from '~/composables/useApi'

// 后端 GET /msg/list 的返回（schemas/msg.py 的 to_mdetail）。
// 公开列表不含 ip —— 后端刻意不下发这个字段。
type AdminMsg = {
  id: number
  user_id: number | null
  content: string
  username: string
  avatar: string | null
  created_at: string
}

const api = useApi()
const toast = useToast()
const route = useRoute()
const router = useRouter()

const size = 20
const page = ref(Number(route.query.page) || 1)

const items = ref<AdminMsg[]>([])
const total = ref(0)
const loading = ref(false)
const errorMsg = ref('')

const pending = ref<AdminMsg | null>(null)
const deleting = ref(false)

function fmt(dt: string) {
  if (!dt) return '——'
  const d = new Date(dt)
  return Number.isNaN(d.getTime()) ? dt : d.toLocaleString('zh-CN', { hour12: false })
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    // 注意分页参数名是 p（不是 page），与后端 Query 声明保持一致
    const data = await api.get<{ total: number; items: AdminMsg[] }>('/msg/list', {
      p: page.value,
      size,
    })
    items.value = data?.items ?? []
    total.value = data?.total ?? 0

    await router.replace({
      query: page.value > 1 ? { page: String(page.value) } : {},
    })
  } catch (err) {
    errorMsg.value = describeError(err)
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

watch(page, () => load())

onMounted(load)

async function confirmDelete() {
  const target = pending.value
  if (!target) return
  deleting.value = true
  try {
    // id 走查询参数：DELETE /msg/del?id=
    await api.del('/msg/del', { id: target.id })
    toast.ok('已删除该留言')
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
        <h1 class="text-xl font-semibold tracking-tight text-slate-900">留言管理</h1>
        <p class="mt-1 text-sm text-slate-500">
          每人限一条，按时间倒序展示；内容已由后端 nh3 白名单消毒，列表不返回来源 IP。
        </p>
      </div>
      <button
        class="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
        @click="load"
      >
        刷新
      </button>
    </header>

    <p v-if="errorMsg" class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {{ errorMsg }}
    </p>

    <div class="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 text-xs text-slate-500">
          <tr>
            <th class="px-4 py-3 text-left font-medium">留言内容</th>
            <th class="px-4 py-3 text-left font-medium w-48">留言者</th>
            <th class="px-4 py-3 text-left font-medium w-44">时间</th>
            <th class="px-4 py-3 text-right font-medium w-24">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="row in items" :key="row.id" class="hover:bg-slate-50/60 transition-colors align-top">
            <td class="px-4 py-3">
              <!-- content 由后端 sanitize_html 消毒后入库，可用 v-html 渲染 -->
              <div class="line-clamp-3 max-w-2xl break-words text-slate-700" v-html="row.content"></div>
            </td>
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <img
                  v-if="row.avatar"
                  :src="row.avatar"
                  alt=""
                  class="h-8 w-8 shrink-0 rounded-full object-cover bg-slate-100"
                >
                <span
                  v-else
                  class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs text-slate-500"
                >
                  {{ (row.username || '?').slice(0, 1) }}
                </span>
                <div class="min-w-0">
                  <p class="truncate text-slate-700">{{ row.username }}</p>
                  <p class="text-[11px] text-slate-400">
                    {{ row.user_id ? `用户 #${row.user_id}` : '账号已删除' }}
                  </p>
                </div>
              </div>
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
            <td colspan="4" class="px-4 py-16 text-center text-sm text-slate-400">
              {{ errorMsg ? '加载失败' : '还没有留言' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AppPagination v-model:page="page" :size="size" :total="total" />

    <!-- 删除确认 -->
    <div v-if="pending" class="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 px-6">
      <div class="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 class="text-base font-semibold text-slate-900">确认删除这条留言？</h2>
        <div class="mt-2 max-h-40 overflow-auto rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600">
          <div class="break-words" v-html="pending.content"></div>
        </div>
        <p class="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700 leading-relaxed">
          后端是硬删除，<strong class="font-semibold">不可恢复</strong>；删除后该用户可以再次留言。
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