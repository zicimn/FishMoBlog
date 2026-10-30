<script setup lang="ts">
import { describeError, errorStatus } from '~/utils/api'
import { COMMENT_MAX_LENGTH, commentTextToHtml } from '~/utils/comment'

// replyTo 只接受顶层评论：后端的 GetList 只取「parent 为顶层评论」的那一层回复，
// 回复一条回复会成功入库但永远不会被列表带出来，所以 UI 不提供这个入口。
const props = withDefaults(
  defineProps<{
    path: string
    replyTo?: { id: number; name: string } | null
  }>(),
  { replyTo: null },
)

const emit = defineEmits<{
  (e: 'submitted'): void
  (e: 'cancel-reply'): void
}>()

const apiBase = useApiBase()
const { token, user, ready, isLoggedIn, logout, clear } = useAuth()

const text = ref('')
const submitting = ref(false)
const errorMsg = ref('')
const successMsg = ref('')
const authOpen = ref(false)

// 计数字符按用户看到的纯文本算；真正提交的是转义后的 HTML，长度可能变长
// （每个 < > & 会变成 4~5 个字符），所以下面还要再核一次编码后的长度。
const textLength = computed(() => text.value.length)
const encodedLength = computed(() => commentTextToHtml(text.value).length)
const tooLong = computed(() => encodedLength.value > COMMENT_MAX_LENGTH)
const canSubmit = computed(
  () =>
    !submitting.value &&
    text.value.trim().length > 0 &&
    !tooLong.value,
)

const initial = computed(() => user.value?.username.trim().charAt(0) || '访')

let successTimer: ReturnType<typeof setTimeout> | null = null

function flashSuccess() {
  successMsg.value = '评论发表成功'
  if (successTimer) clearTimeout(successTimer)
  successTimer = setTimeout(() => {
    successMsg.value = ''
  }, 4000)
}

onBeforeUnmount(() => {
  if (successTimer) clearTimeout(successTimer)
})

// 换文章时清空草稿与提示，避免把上一篇的内容带到下一篇
watch(
  () => props.path,
  () => {
    text.value = ''
    errorMsg.value = ''
    successMsg.value = ''
  },
)

async function submit() {
  if (submitting.value) return

  if (!isLoggedIn.value) {
    authOpen.value = true
    return
  }

  const content = commentTextToHtml(text.value)
  if (!content) {
    errorMsg.value = '评论内容不能为空'
    return
  }
  if (content.length > COMMENT_MAX_LENGTH) {
    errorMsg.value = `内容过长（转义后 ${content.length} / ${COMMENT_MAX_LENGTH} 字符）`
    return
  }

  submitting.value = true
  errorMsg.value = ''
  successMsg.value = ''

  try {
    const body: Record<string, unknown> = { content, path: props.path }
    if (props.replyTo) body.parent_id = props.replyTo.id

    await $fetch('/comments', {
      baseURL: apiBase,
      method: 'POST',
      headers: { Authorization: `Bearer ${token.value}` },
      body,
    })

    text.value = ''
    flashSuccess()
    emit('submitted')
  } catch (err) {
    if (errorStatus(err) === 401) {
      // 令牌过期 / 已在别处登出：清掉本地登录态并直接把登录框推到用户面前，
      // 草稿保留在 textarea 里，重新登录后可以直接再发一次。
      clear()
      authOpen.value = true
      errorMsg.value = '登录已失效，请重新登录后再发表'
    } else {
      errorMsg.value = describeError(err)
    }
  } finally {
    submitting.value = false
  }
}

async function onLogout() {
  await logout()
  text.value = ''
  errorMsg.value = ''
  successMsg.value = ''
  emit('cancel-reply')
}
</script>

<template>
  <section
    class="mt-4 rounded-2xl border border-white/10 bg-white/[0.05] p-5 backdrop-blur-2xl"
    aria-label="发表评论"
  >
    <!-- 登录态还在读取 localStorage：给一个占位，避免先闪「请登录」再变成输入框 -->
    <div v-if="!ready" class="animate-pulse" aria-hidden="true">
      <div class="flex items-center gap-3">
        <div class="h-9 w-9 rounded-full bg-white/10" />
        <div class="space-y-2">
          <div class="h-3 w-32 rounded bg-white/10" />
          <div class="h-2.5 w-24 rounded bg-white/5" />
        </div>
      </div>
    </div>

    <!-- 未登录：只给登录入口，不渲染输入框（后端同样要求登录） -->
    <div
      v-else-if="!isLoggedIn"
      class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div class="flex items-center gap-3">
        <span
          class="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white/[0.06] text-xs text-white/40 ring-1 ring-white/10"
          aria-hidden="true"
        >
          ?
        </span>
        <div class="min-w-0">
          <p class="text-xs font-medium text-white/70">登录后参与评论</p>
          <p class="mt-0.5 text-[11px] text-white/35">
            支持邮箱注册；评论会以账号昵称展示。
          </p>
        </div>
      </div>
      <button
        type="button"
        class="shrink-0 rounded-full border border-sky-300/25 bg-sky-400/15 px-5 py-2 text-xs font-medium text-sky-100 transition hover:bg-sky-400/25 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
        @click="authOpen = true"
      >
        登录 / 注册
      </button>
    </div>

    <!-- 已登录：编辑区 -->
    <form v-else class="space-y-3" @submit.prevent="submit">
      <div class="flex flex-wrap items-center gap-2.5">
        <span
          class="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-gradient-to-br from-sky-500/30 to-fuchsia-500/30 text-xs font-medium text-white/80 ring-1 ring-white/10"
          aria-hidden="true"
        >
          {{ initial }}
        </span>
        <div class="min-w-0">
          <p class="flex items-center gap-1.5 truncate text-xs font-medium text-white/80">
            {{ user?.username }}
            <span
              v-if="user?.is_admin"
              class="rounded-full bg-sky-400/15 px-1.5 py-0.5 text-[10px] font-normal text-sky-200/80 ring-1 ring-inset ring-sky-300/20"
            >
              管理员
            </span>
          </p>
          <p class="truncate text-[11px] text-white/30">{{ user?.email }}</p>
        </div>
        <button
          type="button"
          class="ml-auto text-[11px] text-white/35 transition hover:text-white/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
          @click="onLogout"
        >
          退出
        </button>
      </div>

      <div
        v-if="replyTo"
        class="flex items-center gap-2 rounded-lg border border-sky-300/20 bg-sky-400/10 px-3 py-1.5 text-[11px] text-sky-100/80"
      >
        <span>回复 {{ replyTo.name }}</span>
        <button
          type="button"
          class="ml-auto text-sky-100/50 transition hover:text-white"
          @click="emit('cancel-reply')"
        >
          取消
        </button>
      </div>

      <textarea
        v-model="text"
        rows="4"
        :maxlength="COMMENT_MAX_LENGTH"
        placeholder="写下你的想法…（Ctrl + Enter 发表）"
        class="block w-full resize-y rounded-xl border border-white/10 bg-slate-950/40 px-3.5 py-3 text-sm leading-relaxed text-white/85 outline-none transition placeholder:text-white/20 focus:border-sky-300/30 focus:ring-2 focus:ring-sky-400/15"
        @keydown.ctrl.enter.prevent="submit"
        @keydown.meta.enter.prevent="submit"
      />

      <div class="flex flex-wrap items-center justify-between gap-3">
        <p class="text-[11px]" :class="tooLong ? 'text-rose-300/80' : 'text-white/30'">
          {{ textLength }} / {{ COMMENT_MAX_LENGTH }}
          <span v-if="tooLong" class="ml-1">（转义后超出上限，请删减 &lt; &gt; &amp; 等符号）</span>
        </p>
        <button
          type="submit"
          :disabled="!canSubmit"
          class="rounded-full bg-sky-500/90 px-5 py-2 text-xs font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
        >
          {{ submitting ? '发表中…' : replyTo ? '发表回复' : '发表评论' }}
        </button>
      </div>
    </form>

    <p
      v-if="errorMsg"
      class="mt-3 rounded-xl border border-rose-400/25 bg-rose-500/10 px-3 py-2 text-xs leading-relaxed text-rose-200"
      role="alert"
    >
      {{ errorMsg }}
    </p>
    <p
      v-if="successMsg"
      class="mt-3 rounded-xl border border-emerald-400/25 bg-emerald-500/10 px-3 py-2 text-xs leading-relaxed text-emerald-200"
      role="status"
    >
      {{ successMsg }}
    </p>

    <AuthDialog :open="authOpen" @close="authOpen = false" />
  </section>
</template>