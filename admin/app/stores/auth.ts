import { defineStore } from 'pinia'

// 后端 to_user_info 只回这三个字段（app/schemas/user.py:55）。
type UserInfo = { email: string; username: string; is_admin: boolean }

const TOKEN_KEY = 'blog_admin_token'
const USER_KEY = 'blog_admin_user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const user = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => !!user.value?.is_admin)

  // 令牌放 localStorage：管理端是纯 SPA（nuxt.config 里 ssr:false），
  // 刷新后要能保持登录态。更严的做法是 httpOnly Cookie，但后端令牌是从
  // 响应体下发的，前端没有设置 Cookie 的时机，这里只能如此。
  function restore() {
    if (typeof localStorage === 'undefined') return
    token.value = localStorage.getItem(TOKEN_KEY)
    const raw = localStorage.getItem(USER_KEY)
    if (!raw) return
    try {
      user.value = JSON.parse(raw) as UserInfo
    } catch {
      user.value = null
    }
  }

  function clear() {
    token.value = null
    user.value = null
    if (typeof localStorage === 'undefined') return
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  async function login(email: string, password: string) {
    const config = useRuntimeConfig()
    const res = await $fetch<{ data: Record<string, unknown> }>('/auth/login', {
      baseURL: config.public.apiBase,
      method: 'POST',
      body: { email, password },
    })
    const data = res.data
    token.value = String(data.access_token)
    user.value = {
      email: String(data.email),
      username: String(data.username),
      is_admin: !!data.is_admin,
    }
    localStorage.setItem(TOKEN_KEY, token.value)
    localStorage.setItem(USER_KEY, JSON.stringify(user.value))
  }

  // 登出：后端把 jti 写进 Redis 黑名单；Redis 不可用时后端**失败关闭**会返 403
  // （app/services/auth.py:159）。所以无论成败都清本地态——不清会让用户卡在
  // 「以为登出了、令牌其实还在」的状态里。
  async function logout() {
    try {
      if (token.value) {
        const config = useRuntimeConfig()
        await $fetch('/auth/logout', {
          baseURL: config.public.apiBase,
          method: 'POST',
          headers: { Authorization: `Bearer ${token.value}` },
        })
      }
    } catch {
      // 后端拉黑失败也要让用户离开，本地令牌必须清掉
    } finally {
      clear()
    }
  }

  // 首次拿到 store 时立刻恢复（含刷新页面后的首屏）
  restore()

  return { token, user, isLoggedIn, isAdmin, login, logout, clear, restore }
})