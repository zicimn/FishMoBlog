<script setup lang="ts">
import type { CommentItem, Envelope } from '~/types/blog'

const props = defineProps<{
  path: string
}>()

const config = useRuntimeConfig()
const { isLoggedIn } = useAuth()

const page = ref(1)
const size = 10

// 正在回复的顶层评论。后端列表只带一层回复（child），回复一条回复虽然能入库
// 但永远不会出现在列表里，所以这里只允许对顶层评论发起回复。
const replyTo = ref<{ id: number; name: string } | null>(null)

// GET /comments/{path}?p=&size=：
// 返回 { msg, code, data: [...顶层评论] }，回复在每条的 child 里一次性带出。
// 接口不返回总数，所以「是否还有下一页」只能靠本页是否拿满 size 推断。
const { data, pending, error, refresh } = await useFetch<Envelope<CommentItem[]>>(
  () => `/comments/${encodeURIComponent(props.path)}`,
  {
    baseURL: config.public.apiBase,
    query: { p: page, size },
    watch: [page, () => props.path],
  },
)

const items = computed(() => data.value?.data ?? [])
const hasMore = computed(() => items.value.length >= size)
const showSkeleton = computed(() => pending.value && items.value.length === 0)

function initial(name: string): string {
  return name.trim().charAt(0) || '访'
}

function goTo(target: number) {
  if (target < 1) return
  page.value = target
}

function startReply(comment: CommentItem) {
  replyTo.value = { id: comment.id, name: comment.userName || '访客' }
}

// 新评论按时间倒序排，只在第一页可见；回复则挂在对应顶层评论下。
// 分页停在第一页时直接 refresh（page 没变，useFetch 的 watch 不会触发）；
// 不在第一页就跳回去，由 watch(page) 触发重新请求。
function onSubmitted() {
  const wasReply = replyTo.value !== null
  replyTo.value = null
  if (!wasReply && page.value !== 1) {
    page.value = 1
  } else {
    refresh()
  }
}

// 换文章时回到第一页，并取消未完成的回复目标
watch(
  () => props.path,
  () => {
    page.value = 1
    replyTo.value = null
  },
)
</script>

<template>
  <section class="mt-10" aria-labelledby="comments-heading">
    <div class="flex items-baseline justify-between">
      <h2 id="comments-heading" class="text-sm font-medium tracking-wide text-white/70">
        评论
      </h2>
      <span class="text-[11px] text-white/30">第 {{ page }} 页</span>
    </div>

    <!-- 发表评论（需登录；未登录时显示登录入口） -->
    <CommentComposer
      :path="path"
      :reply-to="replyTo"
      @submitted="onSubmitted"
      @cancel-reply="replyTo = null"
    />

    <!-- 加载中 -->
    <div v-if="showSkeleton" class="mt-4 space-y-3" aria-hidden="true">
      <div
        v-for="n in 3"
        :key="n"
        class="animate-pulse rounded-2xl border border-white/10 bg-white/[0.05] p-5 backdrop-blur-2xl"
      >
        <div class="flex items-center gap-3">
          <div class="h-9 w-9 rounded-full bg-white/10" />
          <div class="space-y-2">
            <div class="h-3 w-24 rounded bg-white/10" />
            <div class="h-2.5 w-16 rounded bg-white/5" />
          </div>
        </div>
        <div class="mt-4 h-3 w-full rounded bg-white/5" />
        <div class="mt-2 h-3 w-2/3 rounded bg-white/5" />
      </div>
    </div>

    <!-- 读取失败 -->
    <div
      v-else-if="error && items.length === 0"
      class="mt-4 rounded-2xl border border-white/10 bg-white/[0.05] px-5 py-10 text-center backdrop-blur-2xl"
    >
      <p class="text-xs text-white/50">评论暂时加载失败</p>
      <button
        type="button"
        class="mt-4 rounded-full border border-white/15 bg-white/10 px-4 py-1.5 text-[11px] text-white/75 transition hover:bg-white/15 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
        @click="refresh()"
      >
        重试
      </button>
    </div>

    <!-- 空态 -->
    <div
      v-else-if="items.length === 0"
      class="mt-4 rounded-2xl border border-white/10 bg-white/[0.05] px-5 py-10 text-center backdrop-blur-2xl"
    >
      <p class="text-xs text-white/40">还没有评论</p>
    </div>

    <!-- 评论列表 -->
    <ul v-else class="mt-4 space-y-3">
      <li
        v-for="comment in items"
        :key="comment.id"
        class="rounded-2xl border border-white/10 bg-white/[0.05] p-5 backdrop-blur-2xl"
      >
        <div class="flex items-center gap-3">
          <img
            v-if="comment.userAvatar"
            :src="comment.userAvatar"
            :alt="comment.userName"
            class="h-9 w-9 rounded-full object-cover ring-1 ring-white/15"
            loading="lazy"
          />
          <span
            v-else
            class="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-sky-500/30 to-fuchsia-500/30 text-xs font-medium text-white/80 ring-1 ring-white/10"
            aria-hidden="true"
          >
            {{ initial(comment.userName) }}
          </span>
          <div class="min-w-0">
            <p class="truncate text-xs font-medium text-white/80">
              {{ comment.userName || '访客' }}
            </p>
            <time class="text-[11px] text-white/30" :datetime="comment.createdDate">
              {{ formatDate(comment.createdDate) }}
            </time>
          </div>
        </div>

        <div
          class="comment-content mt-3 text-sm leading-relaxed text-white/70"
          v-html="comment.content"
        />

        <!-- 回复：后端只带一层，按 parent 顺序返回 -->
        <div
          v-if="comment.child.length"
          class="mt-4 space-y-2 border-l border-white/10 pl-4"
        >
          <div
            v-for="reply in comment.child"
            :key="reply.id"
            class="rounded-xl bg-white/[0.04] px-3 py-2.5"
          >
            <div class="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px]">
              <span class="font-medium text-white/70">{{ reply.userName || '访客' }}</span>
              <span v-if="reply.replyName" class="text-white/30">
                回复 {{ reply.replyName }}
              </span>
              <time class="ml-auto text-white/25" :datetime="reply.createdDate">
                {{ formatDate(reply.createdDate) }}
              </time>
            </div>
            <div
              class="comment-content mt-1.5 text-xs leading-relaxed text-white/60"
              v-html="reply.content"
            />
          </div>
        </div>

        <!-- 只对顶层评论开放回复：回复再回复不会出现在列表里（后端只取一层） -->
        <div v-if="isLoggedIn" class="mt-2 flex justify-end">
          <button
            type="button"
            class="rounded-full px-2.5 py-1 text-[11px] text-white/35 transition hover:bg-white/[0.06] hover:text-sky-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
            @click="startReply(comment)"
          >
            回复
          </button>
        </div>
      </li>
    </ul>

    <nav v-if="items.length" class="mt-6 flex items-center justify-center gap-2" aria-label="评论分页">
      <button
        type="button"
        :disabled="page <= 1"
        class="rounded-full border border-white/10 bg-white/[0.06] px-5 py-2 text-xs text-white/70 backdrop-blur-xl transition hover:bg-white/[0.12] hover:text-white disabled:cursor-not-allowed disabled:opacity-30 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
        @click="goTo(page - 1)"
      >
        上一页
      </button>
      <span class="min-w-16 text-center text-xs tabular-nums text-white/40">{{ page }}</span>
      <button
        type="button"
        :disabled="!hasMore"
        class="rounded-full border border-white/10 bg-white/[0.06] px-5 py-2 text-xs text-white/70 backdrop-blur-xl transition hover:bg-white/[0.12] hover:text-white disabled:cursor-not-allowed disabled:opacity-30 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
        @click="goTo(page + 1)"
      >
        下一页
      </button>
    </nav>
  </section>
</template>