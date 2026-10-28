import { useAuthStore } from '~/stores/auth'

// 后端约定（已核对 app/utils/responsed.py 与各路由）：
//   成功 → 多数端点回 {msg, code, data}，业务数据在 data 里，HTTP 状态码是 200；
//          例外：GET /admin/article/{id} 回裸 dict（见 request 内的兼容分支）。
//   失败 → HTTPException，原因在 body.detail，HTTP 状态码即语义（401/403/404/429/500）。
// 令牌从登录响应体的 access_token 拿，之后一律走 Authorization 请求头
// （后端 HTTPBearer 读的就是请求头）。

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

type Envelope<T> = { msg: string; code: number; data: T }

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  // $fetch 的 body 只接受可序列化对象 / BodyInit，声明成 unknown 会报 TS2322
  body?: Record<string, unknown> | null
  query?: Record<string, unknown>
}

export function useApi() {
  const config = useRuntimeConfig()
  const auth = useAuthStore()

  async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const headers: Record<string, string> = {}
    if (auth.token) headers.Authorization = `Bearer ${auth.token}`

    try {
      const res = await $fetch<Envelope<T>>(path, {
        baseURL: config.public.apiBase,
        method: options.method ?? 'GET',
        body: options.body,
        query: options.query,
        headers,
      })
      // 后端并非所有成功响应都套 {msg, code, data} 信封：
      // GET /admin/article/{id} 直接返回 to_admin_detail 的裸 dict（它和前台
      // /article/{path} 复用了 services/article.py 的 GetId 返回路径），
      // 此时 res.data 不存在。之前无条件取 res.data 会让编辑页的 initial
      // 变成 undefined → ArticleForm/编辑器整块不渲染。
      // 只有确实是信封时才解包，否则原样返回。
      const payload = res as unknown
      if (
        payload !== null &&
        typeof payload === 'object' &&
        !Array.isArray(payload) &&
        'data' in payload &&
        'code' in payload
      ) {
        // data 可能为 null（save/edit/remove 就只回 msg），交给调用方判断
        return (payload as Envelope<T>).data
      }
      return payload as T
    } catch (err) {
      const e = err as { response?: { status?: number }; data?: { detail?: unknown }; message?: string }
      const status = e?.response?.status ?? 0
      // FastAPI 的 422 校验错误 detail 是数组（[{loc, msg, type}]），不是字符串。
      // 只认字符串会退化成 ofetch 的英文原文，这里把每条 msg 拼起来。
      const rawDetail = e?.data?.detail
      const detail = typeof rawDetail === 'string'
        ? rawDetail
        : Array.isArray(rawDetail)
          ? rawDetail
              .map((item) => (item && typeof item === 'object' && 'msg' in item ? String(item.msg) : ''))
              .filter(Boolean)
              .join('；') || '请求参数校验失败'
          : e?.message || '请求失败'

      // 401 = 令牌失效/被拉黑/账号被禁用。清本地态并回登录页，
      // 否则用户会对着一个永远 401 的界面反复点。
      if (status === 401) {
        auth.clear()
        await navigateTo('/login')
      }
      throw new ApiError(detail, status)
    }
  }

  return {
    get: <T>(path: string, query?: Record<string, unknown>) => request<T>(path, { query }),
    post: <T>(path: string, body?: Record<string, unknown> | null) =>
      request<T>(path, { method: 'POST', body }),
    put: <T>(path: string, body?: Record<string, unknown> | null) =>
      request<T>(path, { method: 'PUT', body }),
    // del 必须支持 query：删图接口的 public_id 形如 fishmo_upload/abc123（含斜杠），
    // 做不了路径参数，只能走查询串；$fetch 的 query 通道会自动 encodeURIComponent。
    del: <T>(path: string, query?: Record<string, unknown>) =>
      request<T>(path, { method: 'DELETE', query }),
  }
}

// 把后端过来的状态码翻成一句人话，供页面统一展示。
export function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    // 409 = 唯一索引冲突（后端 Conflict，见 app/utils/responsed.py）。必须先于
    // 500 的语义区分开：以前 slug 撞车是 500，现在明确回 409 并带中文 detail。
    if (err.status === 409) return err.message || '冲突：该路径可能已被占用'
    if (err.status === 403) return err.message || '需要管理员权限'
    if (err.status === 429) return err.message || '操作过于频繁，请稍后再试'
    if (err.status === 401) return err.message || '登录已失效，请重新登录'
    if (err.status === 0) return '连不上后端服务，请确认后端已启动'
    return err.message
  }
  return err instanceof Error ? err.message : '未知错误'
}