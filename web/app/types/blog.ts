// 与后端 app/schemas/article.py 的 to_preview / to_detail 逐字段对齐。
// 后端返回的是普通 dict（不是 response_model），这里只是前端侧的契约声明。
export interface ArticlePreview {
  id: number
  title: string
  // article.path 在库里是 NOT NULL + UNIQUE，前台详情页靠它路由
  path: string
  description: string | null
  cover: string | null
  style: string | null
  views: number
  created_at: string
}

// 详情比列表多 content / updated_at，并且带 cover（to_detail 已补该字段）。
export interface ArticleDetail {
  id: number
  path: string
  cover: string | null
  title: string
  description: string | null
  content: string
  style: string | null
  views: number
  created_at: string
  updated_at: string
}

export interface ArticleListData {
  total: number
  items: ArticlePreview[]
}

// GET /comments/{path} 的条目（后端 schemas/comment.py 的 to_item）。
// 顶层评论分页返回，child 是一次性带出的全部回复（只有一层）。
export interface CommentItem {
  id: number
  userName: string
  userWebsite: string
  userAvatar: string
  // 已经过 nh3 白名单消毒的 HTML
  content: string
  parentId: number | ''
  replyName: string
  createdDate: string
  area: string
  child: CommentItem[]
}

// POST /auth/login、/auth/register 的 data（app/services/auth.py）。
// 作者身份一律由后端从登录态取，前端只负责保存令牌与展示用户名。
export interface AuthUser {
  email: string
  username: string
  is_admin: boolean
}

export interface AuthData extends AuthUser {
  access_token: string
  token_type: string
}

export interface RegisterPayload {
  email: string
  code: string
  username: string
  password: string
  re_password: string
}

// 后端统一信封：{ msg, code, data }（app/utils/responsed.py 的 info）。
export interface Envelope<T> {
  msg: string
  code: number
  data: T
}