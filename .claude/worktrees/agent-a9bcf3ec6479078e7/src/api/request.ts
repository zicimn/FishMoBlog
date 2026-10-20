import axios from "axios"

const request = axios.create({
  baseURL: "/api",   // 使用相对路径，会通过 Nginx 代理到后端
  timeout: 10000, // 添加超时设置
  headers: {
    'Content-Type': 'application/json'
  }
})

request.interceptors.request.use(config => {
  console.log('发送请求:', config.url)
  const token = localStorage.getItem("token")

  if (token) {
    config.headers.Authorization = "Bearer " + token
  }

  return config
}, error => {
  console.error('请求拦截器错误:', error)
  return Promise.reject(error)
})

request.interceptors.response.use(response => {
  console.log('收到响应:', response.config.url, response.status)
  return response
}, error => {
  console.error('响应拦截器错误:', error)
  return Promise.reject(error)
})

export default request