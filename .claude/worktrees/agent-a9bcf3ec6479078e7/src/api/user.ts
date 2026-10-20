import request from './request'

interface LoginRequest {
  username: string
  password: string
}

interface RegisterRequest {
  name: string
  email: string
  password: string
  code: string
}

interface UpdateRequest {
  new_username?: string
  new_email?: string
  new_password?: string
  new_bio?: string
  new_avator?: string
}

interface LoginResponse {
  id: number
  username: string
  access_token: string
  avatar?: string
}

interface UpdateResponse {
  msg: string
  user_id: number
  user?: {
    id: number
    username: string
    avatar?: string
  }
}

interface UserInfoResponse {
  id: number
  username: string
  email: string
  avatar?: string
  bio?: string
}

export const userApi = {
  login: (data: LoginRequest) => request.post<LoginResponse>('/user/login', data),
  register: (data: RegisterRequest) => request.post('/user/register', { name: data.name, email: data.email, password: data.password }, { params: { code: data.code } }),
  update: (data: UpdateRequest) => request.put<UpdateResponse>('/user/update', data),
  delete: (ok: boolean) => request.delete('/user/delete', { params: { ok } }),
  sendCode: (email: string) => request.post('/user/send_code', {}, { params: { email } }),
  retrieve: (email: string, password: string, code: string) => request.post('/user/retrieve', {}, { params: { email, password, code } }),
  updateAvatar: (avatar: string) => request.put<UpdateResponse>('/user/update', { new_avator: avatar }),
  getInfo: () => request.get<UserInfoResponse>('/user/info')
}
