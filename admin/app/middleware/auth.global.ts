// 全局守卫：管理端每个页面都要登录。纯粹是 UI 便利，
// 真正的权限校验在后端（/admin 分组挂了 GetAdminUser，匿名请求一律 401/403）。
export default defineNuxtRouteMiddleware((to) => {
  const auth = useAuthStore()

  if (!auth.isLoggedIn && to.path !== '/login') {
    return navigateTo('/login')
  }
  // 已登录就别停在登录页了
  if (auth.isLoggedIn && to.path === '/login') {
    return navigateTo('/')
  }
})