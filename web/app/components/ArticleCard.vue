<script setup lang="ts">
import type { ArticlePreview } from '~/types/blog'

const props = defineProps<{
  article: ArticlePreview
  index: number
}>()

const formattedDate = computed(() => formatDate(props.article.created_at))

// 没有封面时用标题首字兜底，避免卡片出现一块空白
const initial = computed(() => props.article.title.trim().charAt(0) || '文')

// path 是后端唯一索引，可能包含非 ASCII 字符，交给 router 前先编码
const to = computed(() => `/article/${encodeURIComponent(props.article.path)}`)
</script>

<template>
  <NuxtLink
    :to="to"
    :aria-label="`阅读《${article.title}》`"
    class="group animate-rise relative flex h-[215px] w-full max-w-[345px] flex-col justify-end overflow-hidden rounded-3xl border border-white/10 bg-white/[0.07] shadow-[0_12px_40px_-16px_rgba(2,6,23,0.9)] backdrop-blur-2xl transition duration-500 hover:-translate-y-1.5 hover:border-white/25 hover:shadow-[0_24px_70px_-20px_rgba(2,6,23,0.95)] motion-reduce:transition-none motion-reduce:hover:translate-y-0 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sky-300"
    :style="{ animationDelay: `${Math.min(index, 8) * 70}ms` }"
  >
    <!-- 封面铺满整张卡片，文字直接压在上面 -->
    <img
      v-if="article.cover"
      :src="article.cover"
      :alt="article.title"
      loading="lazy"
      class="absolute inset-0 h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.05]"
    />
    <div
      v-else
      class="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-sky-500/40 via-indigo-500/30 to-fuchsia-500/40"
      aria-hidden="true"
    >
      <span class="text-7xl font-semibold text-white/25">{{ initial }}</span>
    </div>

    <!-- 下半部压暗，保证标题与摘要在任何封面上都能读清 -->
    <div class="absolute inset-0 bg-gradient-to-t from-slate-950/95 via-slate-950/45 to-slate-950/5" />
    <div class="absolute inset-0 bg-white/0 transition-colors duration-500 group-hover:bg-white/[0.04]" />

    <!-- 顶部高光，玻璃边缘的「反光」 -->
    <div class="pointer-events-none absolute inset-x-6 top-0 z-10 h-px bg-gradient-to-r from-transparent via-white/50 to-transparent" />

    <div class="relative z-10 flex flex-col p-6">
      <h2
        class="line-clamp-2 text-lg font-semibold leading-snug text-white [text-shadow:0_2px_12px_rgba(2,6,23,0.6)]"
      >
        {{ article.title }}
      </h2>

      <p
        v-if="article.description"
        class="mt-2 line-clamp-2 text-sm leading-relaxed text-white/65 [text-shadow:0_1px_8px_rgba(2,6,23,0.5)]"
      >
        {{ article.description }}
      </p>

      <!-- 底部一行：日期在左下角，浏览量在右下角 -->
      <div class="mt-4 flex items-center justify-between text-[11px] text-white/55">
        <time :datetime="article.created_at">{{ formattedDate }}</time>
        <span>{{ article.views }} 次浏览</span>
      </div>
    </div>
  </NuxtLink>
</template>