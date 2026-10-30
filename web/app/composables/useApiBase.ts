/**
 * 后端 API 的 baseURL。
 *
 * 两种部署形态（见 nuxt.config.ts）：
 * - 本地 / 测试：浏览器与 SSR 都直连 http://127.0.0.1:8000；
 * - 生产：浏览器走 nginx 同源的 /api，SSR 仍直连后端。
 *
 * 为什么 SSR 不能直接用 `/api`：Nuxt 的 useFetch 在服务端遇到相对 request +
 * 相对 baseURL 时会改用 useRequestFetch()，而 Nitro 的本地 fetch 会把 `/api`
 * 当作 Nuxt 自己的路由（项目没有这个路由），请求不会经过 nginx，最终 404。
 * 所以服务端必须用绝对地址；apiBaseServer 是私有 runtimeConfig，不会下发到
 * 浏览器，避免把内网后端地址暴露给访客。
 */
const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '0.0.0.0', '::1'])

function isLoopback(hostname: string): boolean {
  return LOOPBACK_HOSTS.has(hostname.replace(/^\[|\]$/g, ''))
}

export function useApiBase(): string {
  const config = useRuntimeConfig()
  if (import.meta.server) {
    return config.apiBaseServer || config.public.apiBase
  }

  const base = config.public.apiBase

  // 防呆：如果构建产物把回环地址（127.0.0.1 / localhost）打进了 public 配置——
  // 例如旧产物、或部署时 NUXT_PUBLIC_API_BASE 被误设——访客的浏览器会去连
  // 他自己机器的 8000 端口，必然 `net::ERR_FAILED` + 浏览器侧的 CORS 报错
  // （请求根本没到后端，后端的 CORS 配置也帮不上忙）。
  // 页面本身不在回环地址上时这种地址一定不可用，直接退回同源 /api。
  try {
    const parsed = new URL(base, window.location.origin)
    const pageHost = window.location.hostname
    if (parsed.origin !== window.location.origin && isLoopback(parsed.hostname) && !isLoopback(pageHost)) {
      console.error(
        `[api] public.apiBase="${base}" 指向本机回环地址，线上不可用，已退回同源 /api。` +
          '请用生产配置重新构建（npm run build），或设置 NUXT_PUBLIC_API_BASE。',
      )
      return '/api'
    }
  } catch {
    // base 不是合法 URL（例如本来就配置成 /api），按原值使用
  }

  return base
}

/**
 * 只用于界面文案（「请确认后端已启动（…）」）的 baseURL。
 *
 * 不用 useApiBase()：那在服务端会返回 apiBaseServer，而客户端返回 /api，
 * 后端挂掉时 SSR 出的错误面板在浏览器水合时文本会对不上；这里取 public 值，
 * 两端完全一致，且显示的正是访客浏览器实际访问的地址。
 */
export function useApiBaseLabel(): string {
  return useRuntimeConfig().public.apiBase
}