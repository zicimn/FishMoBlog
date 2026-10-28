// 在 app:mounted 之后才恢复登录态：SSR 阶段读不到 localStorage，若在 setup
// 里直接填值，服务端渲染出的「未登录」与客户端首帧的「已登录」会对不上，
// Vue 会报 hydration mismatch 并丢弃服务端 DOM。挂载完成后再切换则是一次普通更新。
export default defineNuxtPlugin((nuxtApp) => {
  const auth = useAuth()
  nuxtApp.hook('app:mounted', () => {
    auth.init()
  })
})