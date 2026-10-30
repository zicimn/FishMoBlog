<script setup lang="ts">
import { describeError } from '~/composables/useApi'

// 后端 GET /admin/user/list 的返回（schemas/user.py 的 to_admin_user）。
// 只读列表：不含 password_hash；后台不代改他人账号资料 / 状态。
type AdminUser = {
  id: number
  email: string
  username: string
  avatar: string
  bio: string
  is_admin: boolean
  status: number
  created_at: string
}

const api = useApi()
const route = useRoute()
const router = useRouter()

const size = 20
const page = ref(Number(route.query.page) || 1)

const items = ref<AdminUser[]>([])
const total = ref(0)
const loading = ref(false)
const errorMsg = ref('')

function fmt(dt: string) {
  if (!dt) return '——'
  const d = new Date(dt)
  return Number.isNaN(d.getTime()) ? dt : d.toLocaleString('zh-CN', { hour12: false })
}

// user.status：0 禁用 / 1 正常（与评论状态取值不同，不能复用评论页的映射）
function statusMeta(status: number) {
  if (status === 1) {
    return { label: '正常', cls: 'bg-emerald-50 text-emerald-700 ring-emerald-200' }
  }
  if (status === 0) {
    return { label: '禁用', cls: 'bg-rose-50 text-rose-700 ring-rose-200' }
  }
  return { label: `未知(${status})`, cls: 'bg-slate-100 text-slate-500 ring-slate-200' }
}

// bio 是纯文本（后端不做 HTML 消毒，也不应带 HTML 语义），模板里用插值，
// 绝不能用 v-html。
async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await api.get<{ total: number; items: AdminUser[] }>('/admin/user/list', {
      page: page.value,
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
</script>

<template>
  <div class="space-y-6">
    <header class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-xl font-semibold tracking-tight text-slate-900">用户管理</h1>
        <p class="mt-1 text-sm text-slate-500">
          按注册时间倒序展示全部账号；只读列表，不返回密码哈希。自助改资料与注销由前台账号入口完成。
        </p>
      </div>
      <div class="flex shrink-0 items-center gap-3">
        <span v-if="loading" class="text-xs text-slate-400">加载中…</span>
        <button
          class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
          @click="load"
        >
          刷新
        </button>
      </div>
    </header>

    <p v-if="errorMsg" class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {{ errorMsg }}
    </p>

    <div class="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 text-xs text-slate-500">
          <tr>
            <th class="px-4 py-3 text-left font-medium w-56">用户</th>
            <th class="px-4 py-3 text-left font-medium">邮箱</th>
            <th class="px-4 py-3 text-left font-medium">简介</th>
            <th class="px-4 py-3 text-left font-medium w-24">角色</th>
            <th class="px-4 py-3 text-left font-medium w-24">状态</th>
            <th class="px-4 py-3 text-left font-medium w-44">注册时间</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="row in items" :key="row.id" class="hover:bg-slate-50/60 transition-colors align-top">
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
                  <p class="text-[11px] text-slate-400">ID #{{ row.id }}</p>
                </div>
              </div>
            </td>
            <td class="px-4 py-3 text-slate-600">
              <span class="break-all">{{ row.email }}</span>
            </td>
            <td class="px-4 py-3">
              <p class="line-clamp-2 max-w-xs break-words text-slate-600">{{ row.bio || '——' }}</p>
            </td>
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center rounded-full px-2 py-0.5 text-xs ring-1 ring-inset"
                :class="row.is_admin
                  ? 'bg-violet-50 text-violet-700 ring-violet-200'
                  : 'bg-slate-100 text-slate-600 ring-slate-200'"
              >
                {{ row.is_admin ? '管理员' : '访客' }}
              </span>
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
          </tr>
          <tr v-if="!loading && !items.length">
            <td colspan="6" class="px-4 py-16 text-center text-sm text-slate-400">
              {{ errorMsg ? '加载失败' : '还没有用户' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AppPagination v-model:page="page" :size="size" :total="total" />
  </div>
</template>