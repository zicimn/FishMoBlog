<script setup lang="ts">
import { useAuthStore } from '~/stores/auth'
import { describeError } from '~/composables/useApi'

definePageMeta({ layout: 'auth' })

const auth = useAuthStore()
const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function onSubmit() {
  if (!email.value.trim() || !password.value) {
    errorMsg.value = '请填写邮箱与密码'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    await auth.login(email.value.trim(), password.value)
    // 后端不做前端角色区分：非管理员也能登录，只是打后台接口会 403，
    // 所以这里不拦，进去后由界面上方的提示告知。
    await navigateTo(auth.isAdmin ? '/articles' : '/articles')
  } catch (err) {
    errorMsg.value = describeError(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <div class="mb-8">
      <h1 class="text-2xl font-semibold tracking-tight text-slate-900">博客管理后台</h1>
      <p class="mt-1.5 text-sm text-slate-500">请使用管理员账号登录</p>
    </div>

    <form class="space-y-4" @submit.prevent="onSubmit">
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1.5">邮箱</label>
        <input
          v-model="email"
          type="email"
          autocomplete="username"
          maxlength="100"
          class="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none
                 focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
          placeholder="admin@example.com"
        >
      </div>

      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1.5">密码</label>
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          maxlength="128"
          class="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none
                 focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
          placeholder="••••••••"
        >
      </div>

      <p v-if="errorMsg" class="rounded-lg border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-xs text-rose-700">
        {{ errorMsg }}
      </p>

      <button
        type="submit"
        :disabled="loading"
        class="w-full rounded-lg bg-slate-900 px-4 py-3 text-sm font-medium text-white
               hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {{ loading ? '登录中…' : '登录' }}
      </button>
    </form>

    <p class="mt-6 text-xs text-slate-400 leading-relaxed">
      登录限流是 IP + 账号双维度（5 分钟内 10 次），触发后会返回「尝试过于频繁」，
      稍等片刻再试即可。
    </p>
  </div>
</template>