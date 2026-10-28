import type { AuthData, AuthUser, Envelope, RegisterPayload } from '~/types/blog'

// 令牌与用户快照都存在 localStorage：前台是纯浏览器渲染的公开站点，没有
// 服务端会话来兜底；令牌本身来自登录响应体的 access_token（不是响应头）。
// 用户快照只用于「已登录」的界面展示，真正的身份与权限由后端每次回库判定，
// 所以快照被篡改最多让界面显示错名字，不会提权。
const TOKEN_KEY = 'fishmo_access_token'
const USER_KEY = 'fishmo_user'

/**
 * 登录态的唯一出口。
 *
 * 用 useState 而不是 Pinia：前台只有「令牌 + 用户」两个值，且没有任何持久化
 * 逻辑需要中间件，为它引一个状态库不划算。SSR 时状态恒为空（不读 localStorage），
 * 客户端在 `app:mounted` 之后再由 plugins/auth.client.ts 回填，避免水合不一致。
 */
export function useAuth() {
  const config = useRuntimeConfig()
  const token = useState<string>('auth-token', () => '')
  const user = useState<AuthUser | null>('auth-user', () => null)
  // ready 表示「已经尝试读过本地存储」。在那之前不要急着渲染「未登录」，
  // 否则有令牌的访客会先看到登录提示、再闪一下变成输入框。
  const ready = useState<boolean>('auth-ready', () => false)

  const isLoggedIn = computed(() => Boolean(token.value) && user.value !== null)

  function persist(data: AuthData) {
    const nextUser: AuthUser = {
      email: data.email,
      username: data.username,
      is_admin: Boolean(data.is_admin),
    }
    token.value = data.access_token
    user.value = nextUser
    if (import.meta.client) {
      try {
        localStorage.setItem(TOKEN_KEY, data.access_token)
        localStorage.setItem(USER_KEY, JSON.stringify(nextUser))
      } catch {
        // 隐私模式 / 配额满：写不进去也不影响本次会话内的登录态
      }
    }
  }

  function clear() {
    token.value = ''
    user.value = null
    if (!import.meta.client) return
    try {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    } catch {
      // localStorage 被禁用时会直接抛错，内存里的登录态已经清掉就够了
    }
  }

  /** 只在客户端、且只跑一次：从 localStorage 恢复登录态。 */
  function init() {
    if (!import.meta.client || ready.value) return
    ready.value = true
    try {
      const savedToken = localStorage.getItem(TOKEN_KEY) ?? ''
      const rawUser = localStorage.getItem(USER_KEY)
      // 只有一半的数据也视为不可用：单独一条令牌没法渲染用户名，
      // 单独一条用户快照又没有令牌可发请求。
      if (!savedToken || !rawUser) {
        if (savedToken || rawUser) clear()
        return
      }
      const parsed = JSON.parse(rawUser) as Partial<AuthUser> | null
      if (
        !parsed ||
        typeof parsed.email !== 'string' ||
        typeof parsed.username !== 'string' ||
        !parsed.email ||
        !parsed.username
      ) {
        clear()
        return
      }
      token.value = savedToken
      user.value = {
        email: parsed.email,
        username: parsed.username,
        is_admin: Boolean(parsed.is_admin),
      }
    } catch {
      // localStorage 被禁用（隐私模式）或内容被手改成非法 JSON：当作未登录，
      // 不能因为读本地存储失败把整页渲染带崩。
      clear()
    }
  }

  async function login(email: string, password: string) {
    const res = await $fetch<Envelope<AuthData>>('/auth/login', {
      baseURL: config.public.apiBase,
      method: 'POST',
      body: { email, password },
    })
    persist(res.data)
    return res.data
  }

  async function register(payload: RegisterPayload) {
    const res = await $fetch<Envelope<AuthData>>('/auth/register', {
      baseURL: config.public.apiBase,
      method: 'POST',
      body: payload,
    })
    persist(res.data)
    return res.data
  }

  /** 发送注册验证码；返回后端给的过期秒数（用于提示，不用于倒计时）。 */
  async function sendCode(email: string) {
    const res = await $fetch<Envelope<{ expires_in: number }>>('/auth/email-code', {
      baseURL: config.public.apiBase,
      method: 'POST',
      body: { email },
    })
    return res.data
  }

  /**
   * 登出：先清本地、再尽力通知后端拉黑令牌。
   *
   * 后端在 Redis 不可用时对登出「失败关闭」（会回 403），此时本地仍应退出——
   * 否则用户点退出却一直显示已登录。代价是令牌在服务端可能有效到过期，
   * 但令牌只存在当前浏览器里，用户主动丢弃后不存在被别人复用的渠道。
   */
  async function logout() {
    const current = token.value
    clear()
    if (!current) return
    try {
      await $fetch('/auth/logout', {
        baseURL: config.public.apiBase,
        method: 'POST',
        headers: { Authorization: `Bearer ${current}` },
      })
    } catch {
      // 网络失败 / 后端 Redis 故障：本地已经退出，不再向用户报错
    }
  }

  return {
    token,
    user,
    ready,
    isLoggedIn,
    init,
    login,
    register,
    sendCode,
    logout,
    clear,
  }
}