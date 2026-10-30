<script setup lang="ts">
import type { Envelope, MsgItem, MsgListData } from '~/types/blog'
import { describeError, errorStatus } from '~/utils/api'
import { COMMENT_MAX_LENGTH, commentTextToHtml } from '~/utils/comment'

const apiBase = useApiBase()
const apiBaseLabel = useApiBaseLabel()
const { token, user, ready, isLoggedIn, clear } = useAuth()

const page = ref(1)
const size = 10

// GET /msg/list 是公开分页接口，注意分页参数是 p（不是 page）。
// 返回 { msg, code, data: { total, items } }，items 不含 ip。
const { data, pending, error, refresh } = await useFetch<Envelope<MsgListData>>('/msg/list', {
  baseURL: apiBase,
  query: { p: page, size },
  watch: [page],
})

const items = computed(() => data.value?.data?.items ?? [])
const total = computed(() => data.value?.data?.total ?? 0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / size)))
const showSkeleton = computed(() => pending.value && items.value.length === 0)

useHead(() => ({
  title: '留言板 · Fishmo',
  meta: [{ name: 'description', content: '给 Fishmo 留言：一人一条，随便写点什么。' }],
}))

// —— 发表留言 ——
const text = ref('')
const submitting = ref(false)
const composerError = ref('')
const composerOk = ref('')
const authOpen = ref(false)
const profileOpen = ref(false)

const textLength = computed(() => text.value.length)
// 提交的是转义后的 HTML，长度可能变长，所以按编码后的长度再核一次（与评论一致）
const encodedLength = computed(() => commentTextToHtml(text.value).length)
const tooLong = computed(() => encodedLength.value > COMMENT_MAX_LENGTH)
const canSubmit = computed(
  () => !submitting.value && text.value.trim().length > 0 && !tooLong.value,
)

const initial = computed(() => user.value?.username.trim().charAt(0) || '访')

// 当前页里已经有自己的留言时，直接提示「一人一条」，避免提交后才吃 409。
// （自己的留言也可能在别的页，那种情况由后端 409 兜底。）
const hasOwnMessage = computed(
  () => isLoggedIn.value && items.value.some((item) => item.user_id === user.value?.id),
)

function canDelete(item: MsgItem) {
  return (
    isLoggedIn.value &&
    (Boolean(user.value?.is_admin) || item.user_id === user.value?.id)
  )
}

function isMine(item: MsgItem) {
  return Boolean(user.value && item.user_id === user.value.id)
}

// 资料修改入口统一放在「自己的头像」上：未登录时先拉起登录框。
function openProfile() {
  if (!isLoggedIn.value) {
    authOpen.value = true
    return
  }
  profileOpen.value = true
}

function onAvatarClick(item: MsgItem) {
  if (isMine(item)) openProfile()
}

let okTimer: ReturnType<typeof setTimeout> | null = null
function flashOk(message: string) {
  composerOk.value = message
  if (okTimer) clearTimeout(okTimer)
  okTimer = setTimeout(() => {
    composerOk.value = ''
  }, 4000)
}

onBeforeUnmount(() => {
  if (okTimer) clearTimeout(okTimer)
  if (noticeTimer) clearTimeout(noticeTimer)
})

async function submit() {
  if (submitting.value) return
  if (!isLoggedIn.value) {
    authOpen.value = true
    return
  }

  const content = commentTextToHtml(text.value)
  if (!content) {
    composerError.value = '留言内容不能为空'
    return
  }
  if (content.length > COMMENT_MAX_LENGTH) {
    composerError.value = `内容过长（转义后 ${content.length} / ${COMMENT_MAX_LENGTH} 字符）`
    return
  }

  submitting.value = true
  composerError.value = ''
  composerOk.value = ''

  try {
    await $fetch('/msg', {
      baseURL: apiBase,
      method: 'POST',
      headers: { Authorization: `Bearer ${token.value}` },
      body: { content },
    })

    text.value = ''
    flashOk('留言发表成功')
    // 新留言倒序排在最前：回到第 1 页再刷新
    if (page.value !== 1) page.value = 1
    else await refresh()
  } catch (err) {
    if (errorStatus(err) === 401) {
      clear()
      authOpen.value = true
      composerError.value = '登录已失效，请重新登录后再留言'
    } else {
      composerError.value = describeError(err)
    }
  } finally {
    submitting.value = false
  }
}

// —— 分页 ——
function goTo(target: number) {
  const next = Math.min(Math.max(1, target), totalPages.value)
  if (next === page.value) return
  page.value = next
  if (import.meta.client) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// —— 删除自己的留言 ——
const pendingDelete = ref<MsgItem | null>(null)
const deleting = ref(false)
const deleteError = ref('')
const notice = ref('')
let noticeTimer: ReturnType<typeof setTimeout> | null = null

function flashNotice(message: string) {
  notice.value = message
  if (noticeTimer) clearTimeout(noticeTimer)
  noticeTimer = setTimeout(() => {
    notice.value = ''
  }, 3000)
}

function onProfileSaved() {
  flashNotice('资料已更新')
  // 留言里的昵称 / 头像来自发表时的快照，后端不会回写历史留言；
  // 这里刻意不刷新列表，避免让人误以为旧快照也会跟着变。
}

function onProfileUnauthorized() {
  // ProfileDialog 里已经 clear() 过本地登录态，这里只负责把登录框拉起来
  profileOpen.value = false
  authOpen.value = true
  flashNotice('登录已失效，请重新登录')
}

async function confirmDelete() {
  const target = pendingDelete.value
  if (!target) return
  deleting.value = true
  deleteError.value = ''
  try {
    await $fetch('/msg/del', {
      baseURL: apiBase,
      method: 'DELETE',
      query: { id: target.id },
      headers: { Authorization: `Bearer ${token.value}` },
    })
    pendingDelete.value = null
    flashNotice('留言已删除')
    if (items.value.length === 1 && page.value > 1) page.value -= 1
    else await refresh()
  } catch (err) {
    if (errorStatus(err) === 401) {
      clear()
      pendingDelete.value = null
      authOpen.value = true
      flashNotice('登录已失效，请重新登录')
    } else {
      deleteError.value = describeError(err)
    }
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <SiteHeader subtitle="留言" />

    <main class="mx-auto w-full max-w-3xl flex-1 px-5 pb-20 sm:px-8">
      <header class="animate-rise pt-10 sm:pt-14">
        <p class="text-[10px] uppercase tracking-[0.35em] text-white/30">Guestbook</p>
        <h1 class="mt-2 text-3xl font-semibold tracking-tight text-white sm:text-4xl">留言板</h1>
        <p class="mt-3 max-w-xl text-xs leading-relaxed text-white/40 sm:text-sm">
          一人一条，随便写点什么。登录后即可留言，也可以随时删除自己的留言。
        </p>
      </header>

      <!-- 发表留言 -->
      <section
        class="animate-rise mt-8 rounded-3xl border border-white/10 bg-white/[0.06] p-5 shadow-[0_12px_40px_-16px_rgba(2,6,23,0.9)] backdrop-blur-2xl sm:p-6"
        aria-label="发表留言"
      >
        <!-- 登录态还在读取 localStorage：给骨架，避免先闪「未登录」 -->
        <div v-if="!ready" class="animate-pulse" aria-hidden="true">
          <div class="flex items-center gap-3">
            <div class="h-9 w-9 rounded-full bg-white/10" />
            <div class="space-y-2">
              <div class="h-3 w-32 rounded bg-white/10" />
              <div class="h-2.5 w-24 rounded bg-white/5" />
            </div>
          </div>
        </div>

        <!-- 未登录：只给登录入口 -->
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
              <p class="text-xs font-medium text-white/70">登录后留言</p>
              <p class="mt-0.5 text-[11px] text-white/35">
                留言会以账号昵称展示，一人限一条。
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

        <!-- 已登录但当前页已能看到自己的留言 -->
        <div v-else-if="hasOwnMessage" class="flex items-center gap-3">
          <button
            type="button"
            class="h-9 w-9 shrink-0 rounded-full transition hover:ring-2 hover:ring-sky-300/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
            title="修改我的资料"
            aria-label="修改我的资料"
            @click="openProfile"
          >
            <img
              v-if="user?.avatar"
              :src="user.avatar"
              alt=""
              class="h-9 w-9 rounded-full object-cover ring-1 ring-white/15"
            >
            <span
              v-else
              class="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-sky-500/30 to-fuchsia-500/30 text-xs font-medium text-white/80 ring-1 ring-white/10"
              aria-hidden="true"
            >
              {{ initial }}
            </span>
          </button>
          <div class="min-w-0">
            <p class="text-xs font-medium text-white/75">{{ user?.username }}，你已经留过言了</p>
            <p class="mt-0.5 text-[11px] text-white/35">
              每人的留言限一条；删除后可以重新写。点击头像可修改资料。
            </p>
          </div>
        </div>

        <!-- 已登录：编辑区 -->
        <form v-else class="space-y-3" @submit.prevent="submit">
          <div class="flex flex-wrap items-center gap-2.5">
            <button
              type="button"
              class="h-9 w-9 shrink-0 rounded-full transition hover:ring-2 hover:ring-sky-300/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
              title="修改我的资料"
              aria-label="修改我的资料"
              @click="openProfile"
            >
              <img
                v-if="user?.avatar"
                :src="user.avatar"
                alt=""
                class="h-9 w-9 rounded-full object-cover ring-1 ring-white/15"
              >
              <span
                v-else
                class="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-sky-500/30 to-fuchsia-500/30 text-xs font-medium text-white/80 ring-1 ring-white/10"
                aria-hidden="true"
              >
                {{ initial }}
              </span>
            </button>
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
              <p class="truncate text-[11px] text-white/30">
                {{ user?.email }} · <span class="text-white/25">点击头像修改资料</span>
              </p>
            </div>
          </div>

          <textarea
            v-model="text"
            rows="4"
            :maxlength="COMMENT_MAX_LENGTH"
            placeholder="给这个博客留句话吧…（Ctrl + Enter 发表）"
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
              {{ submitting ? '发表中…' : '发表留言' }}
            </button>
          </div>
        </form>

        <p
          v-if="composerError"
          class="mt-3 rounded-xl border border-rose-400/25 bg-rose-500/10 px-3 py-2 text-xs leading-relaxed text-rose-200"
          role="alert"
        >
          {{ composerError }}
        </p>
        <p
          v-if="composerOk"
          class="mt-3 rounded-xl border border-emerald-400/25 bg-emerald-500/10 px-3 py-2 text-xs leading-relaxed text-emerald-200"
          role="status"
        >
          {{ composerOk }}
        </p>
      </section>

      <!-- 留言列表 -->
      <div class="mb-4 mt-10 flex items-end justify-between gap-4">
        <div>
          <p class="text-[10px] uppercase tracking-[0.35em] text-white/30">Messages</p>
          <h2 class="mt-1.5 text-lg font-medium text-white/80">全部留言</h2>
        </div>
        <span class="pb-0.5 text-[11px] tabular-nums text-white/30">
          {{ totalPages > 1 ? `第 ${page} / ${totalPages} 页 · 共 ${total} 条` : `共 ${total} 条` }}
        </span>
      </div>

      <p
        v-if="notice"
        class="mb-4 rounded-xl border border-emerald-400/25 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200"
        role="status"
      >
        {{ notice }}
      </p>

      <!-- 后端不可用 -->
      <section
        v-if="error && items.length === 0"
        class="animate-rise rounded-3xl border border-rose-300/20 bg-rose-500/10 px-6 py-10 text-center backdrop-blur-2xl"
      >
        <p class="text-sm font-medium text-rose-100/90">暂时读不到留言</p>
        <p class="mt-2 text-xs leading-relaxed text-rose-100/50">
          请确认后端已启动（{{ apiBaseLabel }}），然后重试。
        </p>
        <button
          type="button"
          class="mt-6 rounded-full border border-white/15 bg-white/10 px-5 py-2 text-xs font-medium text-white/80 transition hover:bg-white/15 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
          @click="refresh()"
        >
          重试
        </button>
      </section>

      <!-- 骨架 -->
      <div v-else-if="showSkeleton" class="space-y-4" aria-hidden="true">
        <div
          v-for="n in 3"
          :key="n"
          class="h-28 animate-pulse rounded-2xl border border-white/10 bg-white/[0.05] backdrop-blur-2xl"
        />
      </div>

      <!-- 空态 -->
      <section
        v-else-if="items.length === 0"
        class="animate-rise rounded-3xl border border-white/10 bg-white/[0.06] px-6 py-16 text-center backdrop-blur-2xl"
      >
        <p class="text-sm text-white/60">还没有留言</p>
        <p class="mt-2 text-xs text-white/35">登录后写下第一条吧。</p>
      </section>

      <!-- 留言卡片 -->
      <section v-else class="space-y-4">
        <article
          v-for="(item, index) in items"
          :key="item.id"
          class="animate-rise rounded-2xl border border-white/10 bg-white/[0.06] p-5 backdrop-blur-2xl"
          :style="{ animationDelay: `${Math.min(index, 8) * 60}ms` }"
        >
          <div class="flex items-start gap-3">
            <!-- 自己的留言头像可点开资料弹窗；别人的头像不提供入口 -->
            <component
              :is="isMine(item) ? 'button' : 'div'"
              :type="isMine(item) ? 'button' : undefined"
              :title="isMine(item) ? '修改我的资料' : undefined"
              :aria-label="isMine(item) ? '修改我的资料' : undefined"
              class="h-9 w-9 shrink-0 rounded-full transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
              :class="isMine(item) ? 'cursor-pointer hover:ring-2 hover:ring-sky-300/40' : ''"
              @click="onAvatarClick(item)"
            >
              <img
                v-if="item.avatar"
                :src="item.avatar"
                :alt="item.username"
                class="h-9 w-9 rounded-full object-cover ring-1 ring-white/15"
              >
              <span
                v-else
                class="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-sky-500/30 to-fuchsia-500/30 text-xs font-medium text-white/80 ring-1 ring-white/10"
                aria-hidden="true"
              >
                {{ (item.username || '?').trim().charAt(0) || '?' }}
              </span>
            </component>

            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="min-w-0">
                  <p class="truncate text-xs font-medium text-white/80">{{ item.username }}</p>
                  <time class="text-[11px] text-white/30" :datetime="item.created_at">
                    {{ formatDate(item.created_at) }}
                  </time>
                </div>
                <button
                  v-if="canDelete(item)"
                  type="button"
                  class="shrink-0 text-[11px] text-white/30 transition hover:text-rose-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
                  @click="pendingDelete = item; deleteError = ''"
                >
                  删除
                </button>
              </div>

              <!-- content 已由后端 sanitize_html 消毒，可安全用 v-html -->
              <div
                class="mt-2 break-words text-sm leading-relaxed text-white/70 [&_a]:text-sky-300 [&_a]:underline [&_a]:underline-offset-2 [&_b]:text-white/85"
                v-html="item.content"
              />
            </div>
          </div>
        </article>
      </section>

      <nav
        v-if="totalPages > 1"
        class="mt-12 flex items-center justify-center gap-2"
        aria-label="分页"
      >
        <button
          type="button"
          :disabled="page <= 1"
          class="rounded-full border border-white/10 bg-white/[0.06] px-5 py-2 text-xs text-white/70 backdrop-blur-xl transition hover:bg-white/[0.12] hover:text-white disabled:cursor-not-allowed disabled:opacity-30 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
          @click="goTo(page - 1)"
        >
          上一页
        </button>
        <span class="min-w-20 text-center text-xs tabular-nums text-white/40">
          {{ page }} / {{ totalPages }}
        </span>
        <button
          type="button"
          :disabled="page >= totalPages"
          class="rounded-full border border-white/10 bg-white/[0.06] px-5 py-2 text-xs text-white/70 backdrop-blur-xl transition hover:bg-white/[0.12] hover:text-white disabled:cursor-not-allowed disabled:opacity-30 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
          @click="goTo(page + 1)"
        >
          下一页
        </button>
      </nav>
    </main>

    <SiteFooter />

    <!-- ProfileDialog 放在 AuthDialog 前面：401 时两个浮层会在同一 tick
         切换，滚动锁的 watcher 按模板顺序执行，登录框必须最后写 'hidden' -->
    <ProfileDialog
      :open="profileOpen"
      @close="profileOpen = false"
      @saved="onProfileSaved"
      @unauthorized="onProfileUnauthorized"
    />

    <AuthDialog :open="authOpen" @close="authOpen = false" />

    <!-- 删除确认 -->
    <div
      v-if="pendingDelete"
      class="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/60 px-5 backdrop-blur-sm"
    >
      <div class="w-full max-w-sm rounded-2xl border border-white/10 bg-slate-900/90 p-6 shadow-2xl">
        <h2 class="text-sm font-semibold text-white">确认删除这条留言？</h2>
        <div class="mt-3 max-h-36 overflow-auto rounded-xl border border-white/10 bg-white/[0.05] px-3 py-2 text-xs leading-relaxed text-white/60">
          <div class="break-words" v-html="pendingDelete.content" />
        </div>
        <p class="mt-3 text-[11px] leading-relaxed text-white/35">
          删除后该账号可以重新留言；操作不可恢复。
        </p>
        <p v-if="deleteError" class="mt-3 rounded-lg border border-rose-400/25 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
          {{ deleteError }}
        </p>
        <div class="mt-5 flex justify-end gap-3">
          <button
            type="button"
            class="rounded-full border border-white/10 px-4 py-2 text-xs text-white/60 transition hover:bg-white/[0.08] hover:text-white"
            @click="pendingDelete = null"
          >
            取消
          </button>
          <button
            type="button"
            :disabled="deleting"
            class="rounded-full bg-rose-500/90 px-4 py-2 text-xs font-medium text-slate-950 transition hover:bg-rose-400 disabled:cursor-not-allowed disabled:opacity-50"
            @click="confirmDelete"
          >
            {{ deleting ? '删除中…' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>