<script setup lang="ts">
import type { AuthUser, Envelope } from '~/types/blog'
import { describeError, errorStatus } from '~/utils/api'

// 修改自己的资料（用户名 / 头像 / 简介）。入口在留言板：点自己的头像。
// 邮箱、密码、权限都不在这里改——后端 UserEditRequest 用 extra="forbid"
// 拒绝这些字段，前端也就不提供入口。
const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved'): void
  (e: 'unauthorized'): void
}>()

const apiBase = useApiBase()
const { token, user, clear, applyProfile } = useAuth()

const form = reactive({ username: '', avatar: '', bio: '' })
// 打开弹窗时的快照，用来判断哪些字段真的改了。后端对可空字段的语义是
// 「键不出现 = 不改，键出现且为 null / 空串 = 清空」，所以只发改动过的键，
// 避免本地快照缺字段时「只改用户名」把头像 / 简介一起清掉。
const original = reactive({ username: '', avatar: '', bio: '' })

const loading = ref(false)
const errorMsg = ref('')
const avatarBroken = ref(false)
const usernameInput = ref<HTMLInputElement | null>(null)

const initial = computed(() => form.username.trim().charAt(0) || '访')
const avatarPreview = computed(() => form.avatar.trim())

const avatarValid = computed(() => {
  const value = avatarPreview.value
  if (!value) return true
  try {
    const parsed = new URL(value)
    return (
      (parsed.protocol === 'http:' || parsed.protocol === 'https:') &&
      Boolean(parsed.hostname)
    )
  } catch {
    return false
  }
})

const hasChanges = computed(
  () =>
    form.username.trim() !== original.username ||
    form.avatar.trim() !== original.avatar ||
    form.bio.trim() !== original.bio,
)

const bioLength = computed(() => form.bio.length)

function reset() {
  const current = user.value
  form.username = current?.username ?? ''
  form.avatar = current?.avatar ?? ''
  form.bio = current?.bio ?? ''
  original.username = form.username.trim()
  original.avatar = form.avatar.trim()
  original.bio = form.bio.trim()
  loading.value = false
  errorMsg.value = ''
  avatarBroken.value = false
}

watch(
  () => props.open,
  async (open) => {
    if (!open) {
      loading.value = false
      return
    }
    reset()
    await nextTick()
    if (import.meta.client) usernameInput.value?.focus()
  },
  { immediate: true },
)

// 头像预览加载失败时退回昵称首字，避免弹窗里出现破图
watch(
  () => form.avatar,
  () => {
    avatarBroken.value = false
  },
)

// 浮层打开期间锁住底层页面滚动（与 AuthDialog 一致）
watch(
  () => props.open,
  (open) => {
    if (!import.meta.client) return
    document.body.style.overflow = open ? 'hidden' : ''
  },
  { immediate: true },
)
onBeforeUnmount(() => {
  if (import.meta.client) document.body.style.overflow = ''
})

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.open && !loading.value) emit('close')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

function close() {
  if (loading.value) return
  emit('close')
}

function validate(): string {
  const username = form.username.trim()
  if (username.length < 2) return '用户名至少 2 个字符'
  if (username.length > 50) return '用户名最多 50 个字符'
  if (/\s/.test(username)) return '用户名不能包含空白字符'

  const avatar = form.avatar.trim()
  if (avatar.length > 255) return '头像地址最多 255 个字符'
  if (avatar && !avatarValid.value) return '头像地址必须是 http(s) 链接'

  if (form.bio.trim().length > 200) return '简介最多 200 个字符'
  return ''
}

async function onSubmit() {
  if (loading.value) return
  errorMsg.value = ''

  const problem = validate()
  if (problem) {
    errorMsg.value = problem
    return
  }

  const username = form.username.trim()
  const avatar = form.avatar.trim()
  const bio = form.bio.trim()

  const payload: { username?: string; avatar?: string | null; bio?: string | null } = {}
  if (username !== original.username) payload.username = username
  if (avatar !== original.avatar) payload.avatar = avatar || null
  if (bio !== original.bio) payload.bio = bio || null

  if (!Object.keys(payload).length) {
    emit('close')
    return
  }

  loading.value = true
  try {
    const res = await $fetch<Envelope<AuthUser>>('/user/profile', {
      baseURL: apiBase,
      method: 'PUT',
      headers: { Authorization: `Bearer ${token.value}` },
      body: payload,
    })
    applyProfile({
      username: res.data.username,
      avatar: res.data.avatar,
      bio: res.data.bio,
    })
    emit('saved')
    emit('close')
  } catch (err) {
    if (errorStatus(err) === 401) {
      clear()
      emit('unauthorized')
      emit('close')
    } else {
      errorMsg.value = describeError(err)
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 overflow-y-auto overscroll-contain bg-slate-950/70 px-4 py-10 backdrop-blur-sm"
      @click.self="close"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="修改个人资料"
        class="mx-auto w-full max-w-lg rounded-3xl border border-white/10 bg-slate-900/85 p-6 shadow-[0_24px_80px_-24px_rgba(2,6,23,0.95)] backdrop-blur-2xl sm:p-8"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-[10px] uppercase tracking-[0.3em] text-sky-200/50">Profile</p>
            <h2 class="mt-2 text-xl font-semibold tracking-tight text-white">修改个人资料</h2>
            <p class="mt-1.5 text-xs leading-relaxed text-white/40">
              在留言板点击自己的头像即可打开；邮箱与密码不在此处修改。
            </p>
          </div>
          <button
            type="button"
            aria-label="关闭"
            class="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-white/10 bg-white/[0.06] text-white/50 transition hover:bg-white/[0.12] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
            @click="close"
          >
            <svg viewBox="0 0 20 20" fill="none" class="h-3.5 w-3.5" aria-hidden="true">
              <path
                d="M4 4l12 12M16 4L4 16"
                stroke="currentColor"
                stroke-width="1.6"
                stroke-linecap="round"
              />
            </svg>
          </button>
        </div>

        <form class="mt-6 space-y-5" @submit.prevent="onSubmit">
          <div class="flex items-start gap-4">
            <div
              class="grid h-16 w-16 shrink-0 place-items-center overflow-hidden rounded-full bg-gradient-to-br from-sky-500/30 to-fuchsia-500/30 text-lg font-medium text-white/80 ring-1 ring-white/15"
              aria-hidden="true"
            >
              <img
                v-if="avatarPreview && avatarValid && !avatarBroken"
                :src="avatarPreview"
                alt=""
                class="h-full w-full object-cover"
                @error="avatarBroken = true"
              >
              <span v-else>{{ initial }}</span>
            </div>

            <label class="min-w-0 flex-1">
              <span class="text-[11px] text-white/45">头像地址</span>
              <input
                v-model="form.avatar"
                type="text"
                inputmode="url"
                maxlength="255"
                autocomplete="url"
                placeholder="https://…（留空则显示昵称首字）"
                class="mt-1.5 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3.5 py-2.5 text-sm text-white outline-none transition placeholder:text-white/20 focus:border-sky-300/40 focus:ring-2 focus:ring-sky-400/20"
              >
              <span
                v-if="form.avatar.trim() && !avatarValid"
                class="mt-1 block text-[11px] text-rose-300/80"
              >
                头像地址必须是 http(s) 链接
              </span>
              <span
                v-else-if="avatarBroken"
                class="mt-1 block text-[11px] text-amber-300/70"
              >
                图片加载失败，请检查链接；仍可保存。
              </span>
            </label>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <label class="block">
              <span class="text-[11px] text-white/45">用户名</span>
              <input
                ref="usernameInput"
                v-model="form.username"
                maxlength="50"
                autocomplete="nickname"
                placeholder="留言里显示的名字"
                class="mt-1.5 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3.5 py-2.5 text-sm text-white outline-none transition placeholder:text-white/20 focus:border-sky-300/40 focus:ring-2 focus:ring-sky-400/20"
              >
            </label>

            <label class="block">
              <span class="text-[11px] text-white/45">邮箱</span>
              <input
                :value="user?.email ?? ''"
                type="email"
                readonly
                class="mt-1.5 w-full cursor-not-allowed rounded-xl border border-white/5 bg-white/[0.03] px-3.5 py-2.5 text-sm text-white/40 outline-none"
              >
            </label>
          </div>

          <label class="block">
            <span class="text-[11px] text-white/45">简介</span>
            <textarea
              v-model="form.bio"
              rows="3"
              maxlength="200"
              placeholder="一句话介绍自己（纯文本，不会公开邮箱）"
              class="mt-1.5 block w-full resize-y rounded-xl border border-white/10 bg-slate-950/50 px-3.5 py-3 text-sm leading-relaxed text-white/85 outline-none transition placeholder:text-white/20 focus:border-sky-300/40 focus:ring-2 focus:ring-sky-400/20"
            />
          </label>
          <p class="-mt-2 text-right text-[11px] tabular-nums text-white/25">
            {{ bioLength }} / 200
          </p>

          <p class="rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2 text-[11px] leading-relaxed text-white/35">
            用户名修改后，历史留言与评论仍显示发布当时的昵称与头像快照。
          </p>

          <p
            v-if="errorMsg"
            class="rounded-xl border border-rose-400/25 bg-rose-500/10 px-3 py-2 text-xs leading-relaxed text-rose-200"
            role="alert"
          >
            {{ errorMsg }}
          </p>

          <div class="flex justify-end gap-3">
            <button
              type="button"
              :disabled="loading"
              class="rounded-full border border-white/10 px-4 py-2 text-xs text-white/60 transition hover:bg-white/[0.08] hover:text-white disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
              @click="close"
            >
              取消
            </button>
            <button
              type="submit"
              :disabled="loading || !hasChanges"
              class="rounded-full bg-sky-500/90 px-5 py-2 text-xs font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
            >
              {{ loading ? '保存中…' : '保存修改' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>