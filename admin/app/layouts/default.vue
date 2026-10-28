<script setup lang="ts">
import { useAuthStore } from '~/stores/auth'

const auth = useAuthStore()
const toast = useToast()
const route = useRoute()

const nav = [
  { to: '/articles', label: '文章管理', hint: '列表 · 增删改' },
  { to: '/articles/new', label: '写新文章', hint: '正文 · 状态' },
]

// 用 startsWith 而不是全等：/articles/12/edit 也要点亮「文章管理」，
// 但 /articles/new 要归到「写新文章」，所以把更具体的路径排在前面判断。
function isActive(to: string) {
  if (to === '/articles/new') return route.path === '/articles/new'
  return route.path === to || route.path.startsWith(`${to}/`)
}

async function onLogout() {
  await auth.logout()
  toast.ok('已退出登录')
  await navigateTo('/login')
}
</script>

<template>
  <div class="min-h-screen flex bg-slate-100">
    <!-- 侧栏 -->
    <aside class="w-60 shrink-0 bg-slate-900 text-slate-300 flex flex-col">
      <div class="px-5 py-5 border-b border-white/10">
        <p class="text-white font-semibold tracking-tight">博客后台</p>
        <p class="text-xs text-slate-400 mt-1">FastAPI · Admin</p>
      </div>

      <nav class="flex-1 px-3 py-4 space-y-1">
        <NuxtLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="block rounded-lg px-3 py-2.5 transition-colors"
          :class="isActive(item.to)
            ? 'bg-white/10 text-white'
            : 'text-slate-300 hover:bg-white/5 hover:text-white'"
        >
          <span class="block text-sm font-medium">{{ item.label }}</span>
          <span class="block text-[11px] text-slate-400 mt-0.5">{{ item.hint }}</span>
        </NuxtLink>
      </nav>

      <div class="px-4 py-4 border-t border-white/10">
        <p class="text-xs text-slate-400">当前账号</p>
        <p class="text-sm text-white truncate">{{ auth.user?.username || '——' }}</p>
        <p class="text-[11px] text-slate-400 truncate">{{ auth.user?.email }}</p>
        <!-- 只用于提示：真正的权限判断在后端，非管理员打 /admin/* 会被 403 -->
        <p v-if="auth.user && !auth.isAdmin" class="mt-2 text-[11px] text-amber-400 leading-snug">
          该账号不是管理员，后台接口会返回 403
        </p>
        <button
          class="mt-3 w-full rounded-lg border border-white/15 px-3 py-1.5 text-xs text-slate-200 hover:bg-white/10 transition-colors"
          @click="onLogout"
        >
          退出登录
        </button>
      </div>
    </aside>

    <!-- 内容区 -->
    <div class="flex-1 min-w-0 flex flex-col">
      <main class="flex-1 px-8 py-7">
        <slot />
      </main>
      <footer class="px-8 py-4 text-xs text-slate-400">
        管理端 dev 端口 3001，后端默认 127.0.0.1:8000
      </footer>
    </div>

    <!-- 全局提示 -->
    <div class="fixed top-5 right-5 z-50 space-y-2 w-80">
      <div
        v-for="t in toast.items.value"
        :key="t.id"
        class="rounded-lg px-4 py-3 text-sm shadow-lg border cursor-pointer"
        :class="t.kind === 'ok'
          ? 'bg-white border-emerald-200 text-emerald-800'
          : 'bg-white border-rose-200 text-rose-700'"
        @click="toast.dismiss(t.id)"
      >
        {{ t.text }}
      </div>
    </div>
  </div>
</template>