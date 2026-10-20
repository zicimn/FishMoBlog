import { createRouter, createWebHistory } from "vue-router"

const routes = [
  {
    path: "/",
    component: () => import("@/views/HomePage.vue")
  },
  {
    path: "/login",
    component: () => import("@/views/LoginPage.vue")
  },
  {
    path: "/register",
    component: () => import("@/views/RegisterPage.vue")
  },
  {
    path: "/article/:id",
    component: () => import("@/views/ArticleDetail.vue")
  },
  {
    path: "/publish",
    component: () => import("@/views/PublishArticle.vue")
  },
  {
    path: "/edit/:id",
    component: () => import("@/views/EditArticle.vue")
  },
  {
    path: "/profile",
    component: () => import("@/views/UserProfile.vue")
  },
  {
    path: "/articles",
    component: () => import("@/views/UserArticles.vue")
  },
  {
    path: "/control",
    component: () => import("@/views/ControlPanel.vue")
  },
  {
    path: "/links",
    component: () => import("@/views/UserLinks.vue")
  },
  {
    path: "/favorite",
    component: () => import("@/views/FavoritePage.vue")
  },
  {
    path: "/forgot-password",
    component: () => import("@/views/ForgotPasswordPage.vue")
  },
  {
    path: "/search/:word",
    component: () => import("@/views/SearchResults.vue")
  },
  {
    path: "/tools",
    component: () => import("@/views/ToolsPage.vue")
  },
  {
    path: "/user-home",
    component: () => import("@/views/UserHome.vue")
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router