<script setup lang="ts">
import { describeError } from '~/utils/api'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const { login, register, sendCode } = useAuth()

const mode = ref<'login' | 'register'>('login')
const loading = ref(false)
const errorMsg = ref('')
const hintMsg = ref('')

const loginForm = reactive({ email: '', password: '' })
const regForm = reactive({
  email: '',
  code: '',
  username: '',
  password: '',
  re_password: '',
})

// 验证码倒计时：后端对同一邮箱有 60 秒冷却，前端同步倒计时避免点了没反应
const sendingCode = ref(false)
const countdown = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

const emailInput = ref<HTMLInputElement | null>(null)
const regEmailInput = ref<HTMLInputElement | null>(null)

function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function startCountdown(seconds = 60) {
  stopTimer()
  countdown.value = Math.max(1, seconds)
  timer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) stopTimer()
  }, 1000)
}

onBeforeUnmount(stopTimer)

watch(
  () => props.open,
  async (open) => {
    if (!open) {
      stopTimer()
      loading.value = false
      sendingCode.value = false
      errorMsg.value = ''
      hintMsg.value = ''
      return
    }
    // 打开时把焦点放到邮箱框：登录与注册两个表单的邮箱框不是同一个元素
    await nextTick()
    if (mode.value === 'login') emailInput.value?.focus()
    else regEmailInput.value?.focus()
  },
)

// 浮层打开期间锁住底层页面滚动（与站内其它浮层一致）
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

// Esc 关闭：与站内其它浮层（管理端预览）保持同一手感
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.open && !loading.value) emit('close')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

function close() {
  if (loading.value) return
  emit('close')
}

function switchMode(next: 'login' | 'register') {
  if (mode.value === next) return
  mode.value = next
  errorMsg.value = ''
  hintMsg.value = ''
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

async function onLogin() {
  if (loading.value) return
  errorMsg.value = ''
  hintMsg.value = ''

  const email = loginForm.email.trim()
  if (!EMAIL_RE.test(email)) {
    errorMsg.value = '请填写正确的邮箱地址'
    return
  }
  if (!loginForm.password) {
    errorMsg.value = '请填写密码'
    return
  }

  loading.value = true
  try {
    await login(email, loginForm.password)
    loginForm.password = ''
    emit('close')
  } catch (err) {
    errorMsg.value = describeError(err)
  } finally {
    loading.value = false
  }
}

// 与后端 RegisterRequest 的规则保持一致；提前在前端拦一遍，用户才能看到
// 中文原因（FastAPI 内置校验的错误文案是英文，前端会退化成通用提示）。
function validateRegister(): string {
  const email = regForm.email.trim()
  const username = regForm.username.trim()

  if (!EMAIL_RE.test(email)) return '请填写正确的邮箱地址'
  if (!/^\d{6}$/.test(regForm.code.trim())) return '验证码是 6 位数字'
  if (username.length < 2) return '用户名至少 2 个字符'
  if (/\s/.test(username)) return '用户名不能包含空白字符'
  if (regForm.password.length < 8) return '密码至少 8 位'
  if (!/[A-Za-z]/.test(regForm.password) || !/\d/.test(regForm.password)) {
    return '密码需同时包含字母和数字'
  }
  if (regForm.password !== regForm.re_password) return '两次输入的密码不一致'
  return ''
}

async function onRegister() {
  if (loading.value) return
  errorMsg.value = ''
  hintMsg.value = ''

  const problem = validateRegister()
  if (problem) {
    errorMsg.value = problem
    return
  }

  loading.value = true
  try {
    await register({
      email: regForm.email.trim(),
      code: regForm.code.trim(),
      username: regForm.username.trim(),
      password: regForm.password,
      re_password: regForm.re_password,
    })
    regForm.password = ''
    regForm.re_password = ''
    emit('close')
  } catch (err) {
    errorMsg.value = describeError(err)
  } finally {
    loading.value = false
  }
}

async function onSendCode() {
  if (sendingCode.value || countdown.value > 0) return
  errorMsg.value = ''
  hintMsg.value = ''

  const email = regForm.email.trim()
  if (!EMAIL_RE.test(email)) {
    errorMsg.value = '请先填写正确的邮箱地址'
    return
  }

  sendingCode.value = true
  try {
    const data = await sendCode(email)
    const minutes = Math.max(1, Math.ceil((data?.expires_in ?? 300) / 60))
    hintMsg.value = `验证码已发送，${minutes} 分钟内有效`
    startCountdown(60)
  } catch (err) {
    errorMsg.value = describeError(err)
  } finally {
    sendingCode.value = false
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
        aria-label="登录或注册"
        class="mx-auto w-full max-w-md rounded-3xl border border-white/10 bg-slate-900/85 p-6 shadow-[0_24px_80px_-24px_rgba(2,6,23,0.95)] backdrop-blur-2xl sm:p-8"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-[10px] uppercase tracking-[0.3em] text-sky-200/50">Account</p>
            <h2 class="mt-2 text-xl font-semibold tracking-tight text-white">
              {{ mode === 'login' ? '登录后参与评论' : '注册一个账号' }}
            </h2>
            <p class="mt-1.5 text-xs leading-relaxed text-white/40">
              {{ mode === 'login'
                ? '评论需要登录账号；管理员账号同样从这里进入。'
                : '注册后即可发表评论，邮箱仅用于验证，不会公开。' }}
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

        <!-- 登录 / 注册 切换 -->
        <div class="mt-5 grid grid-cols-2 gap-1 rounded-xl border border-white/10 bg-white/[0.04] p-1">
          <button
            v-for="tab in ([
              { key: 'login', label: '登录' },
              { key: 'register', label: '注册' },
            ] as const)"
            :key="tab.key"
            type="button"
            class="rounded-lg px-3 py-2 text-xs transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
            :class="mode === tab.key
              ? 'bg-white/[0.12] text-white shadow-sm'
              : 'text-white/45 hover:text-white/70'"
            @click="switchMode(tab.key)"
          >
            {{ tab.label }}
          </button>
        </div>

        <p
          v-if="errorMsg"
          class="mt-4 rounded-xl border border-rose-400/25 bg-rose-500/10 px-3 py-2 text-xs leading-relaxed text-rose-200"
          role="alert"
        >
          {{ errorMsg }}
        </p>
        <p
          v-if="hintMsg"
          class="mt-4 rounded-xl border border-sky-400/25 bg-sky-500/10 px-3 py-2 text-xs leading-relaxed text-sky-100/80"
        >
          {{ hintMsg }}
        </p>

        <form v-if="mode === 'login'" class="mt-5 space-y-4" @submit.prevent="onLogin">
          <label class="block">
            <span class="text-[11px] text-white/45">邮箱</span>
            <input
              ref="emailInput"
              v-model="loginForm.email"
              type="email"
              autocomplete="email"
              placeholder="you@example.com"
              class="mt-1.5 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3.5 py-2.5 text-sm text-white outline-none transition placeholder:text-white/20 focus:border-sky-300/40 focus:ring-2 focus:ring-sky-400/20"
            />
          </label>

          <label class="block">
            <span class="text-[11px] text-white/45">密码</span>
            <input
              v-model="loginForm.password"
              type="password"
              autocomplete="current-password"
              placeholder="••••••••"
              class="mt-1.5 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3.5 py-2.5 text-sm text-white outline-none transition placeholder:text-white/20 focus:border-sky-300/40 focus:ring-2 focus:ring-sky-400/20"
            />
          </label>

          <button
            type="submit"
            :disabled="loading"
            class="w-full rounded-xl bg-sky-500/90 px-4 py-2.5 text-sm font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
          >
            {{ loading ? '登录中…' : '登录' }}
          </button>
        </form>

        <form v-else class="mt-5 space-y-4" @submit.prevent="onRegister">
          <label class="block">
            <span class="text-[11px] text-white/45">邮箱</span>
            <div class="mt-1.5 flex gap-2">
              <input
                ref="regEmailInput"
                v-model="regForm.email"
                type="email"
                autocomplete="email"
                placeholder="you@example.com"
                class="min-w-0 flex-1 rounded-xl border border-white/10 bg-slate-950/50 px-3.5 py-2.5 text-sm text-white outline-none transition placeholder:text-white/20 focus:border-sky-300/40 focus:ring-2 focus:ring-sky-400/20"
              />
              <button
                type="button"
                :disabled="sendingCode || countdown > 0"
                class="shrink-0 rounded-xl border border-white/15 bg-white/[0.06] px-3 py-2 text-[11px] text-white/70 transition hover:bg-white/[0.12] hover:text-white disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
                @click="onSendCode"
              >
                {{ countdown > 0 ? `${countdown}s 后重发` : sendingCode ? '发送中…' : '获取验证码' }}
              </button>
            </div>
          </label>

          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="text-[11px] text-white/45">验证码</span>
              <input
                v-model="regForm.code"
                inputmode="numeric"
                maxlength="6"
                autocomplete="one-time-code"
                placeholder="6 位数字"
                class="mt-1.5 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3.5 py-2.5 text-sm tracking-[0.2em] text-white outline-none transition placeholder:tracking-normal placeholder:text-white/20 focus:border-sky-300/40 focus:ring-2 focus:ring-sky-400/20"
              />
            </label>
            <label class="block">
              <span class="text-[11px] text-white/45">用户名</span>
              <input
                v-model="regForm.username"
                maxlength="50"
                autocomplete="nickname"
                placeholder="评论里显示的名字"
                class="mt-1.5 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3.5 py-2.5 text-sm text-white outline-none transition placeholder:text-white/20 focus:border-sky-300/40 focus:ring-2 focus:ring-sky-400/20"
              />
            </label>
          </div>

          <label class="block">
            <span class="text-[11px] text-white/45">密码</span>
            <input
              v-model="regForm.password"
              type="password"
              autocomplete="new-password"
              maxlength="128"
              placeholder="至少 8 位，需含字母和数字"
              class="mt-1.5 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3.5 py-2.5 text-sm text-white outline-none transition placeholder:text-white/20 focus:border-sky-300/40 focus:ring-2 focus:ring-sky-400/20"
            />
          </label>

          <label class="block">
            <span class="text-[11px] text-white/45">确认密码</span>
            <input
              v-model="regForm.re_password"
              type="password"
              autocomplete="new-password"
              maxlength="128"
              placeholder="再输入一次密码"
              class="mt-1.5 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3.5 py-2.5 text-sm text-white outline-none transition placeholder:text-white/20 focus:border-sky-300/40 focus:ring-2 focus:ring-sky-400/20"
            />
          </label>

          <button
            type="submit"
            :disabled="loading"
            class="w-full rounded-xl bg-sky-500/90 px-4 py-2.5 text-sm font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
          >
            {{ loading ? '注册中…' : '注册并登录' }}
          </button>
        </form>

        <p class="mt-5 text-[11px] leading-relaxed text-white/25">
          登录状态保存在当前浏览器；令牌有效期 7 天，退出后即失效。
        </p>
      </div>
    </div>
  </Teleport>
</template>