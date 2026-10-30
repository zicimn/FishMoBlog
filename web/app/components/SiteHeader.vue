<script setup lang="ts">
withDefaults(defineProps<{ subtitle?: string }>(), {
  subtitle: '写点东西，留给时间',
})

const route = useRoute()

// 文章详情也归在「文章」这一项下
const onHome = computed(() => route.path === '/')
const onArticles = computed(
  () => route.path.startsWith('/articles') || route.path.startsWith('/article'),
)
const onGuestbook = computed(() => route.path.startsWith('/guestbook'))
const onAbout = computed(() => route.path.startsWith('/about'))
</script>

<template>
  <header class="px-5 pt-6 sm:px-8">
    <div class="mx-auto flex max-w-6xl items-center justify-between rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3 backdrop-blur-xl sm:px-6">
      <NuxtLink to="/" class="flex items-center gap-3">
        <img
          src="/ico.jpg"
          alt="站点图标"
          class="h-9 w-9 rounded-xl object-cover ring-1 ring-white/20"
        />
        <span class="text-sm font-medium tracking-wide text-white/80">Fishmo · 博客</span>
      </NuxtLink>
      <div class="flex items-center gap-2 sm:gap-4">
        <span class="hidden text-xs text-white/40 md:block">{{ subtitle }}</span>

        <nav
          class="flex items-center gap-0.5 rounded-full border border-white/10 bg-white/[0.04] p-1"
          aria-label="主导航"
        >
          <NuxtLink
            to="/"
            class="rounded-full px-2.5 py-1.5 text-[11px] transition sm:px-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
            :class="onHome ? 'bg-white/[0.12] text-white' : 'text-white/45 hover:text-white/80'"
          >
            首页
          </NuxtLink>
          <NuxtLink
            to="/articles"
            class="rounded-full px-2.5 py-1.5 text-[11px] transition sm:px-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
            :class="onArticles ? 'bg-white/[0.12] text-white' : 'text-white/45 hover:text-white/80'"
          >
            文章
          </NuxtLink>
          <NuxtLink
            to="/guestbook"
            class="rounded-full px-2.5 py-1.5 text-[11px] transition sm:px-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
            :class="onGuestbook ? 'bg-white/[0.12] text-white' : 'text-white/45 hover:text-white/80'"
          >
            留言
          </NuxtLink>
          <NuxtLink
            to="/about"
            class="rounded-full px-2.5 py-1.5 text-[11px] transition sm:px-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
            :class="onAbout ? 'bg-white/[0.12] text-white' : 'text-white/45 hover:text-white/80'"
          >
            关于
          </NuxtLink>
        </nav>
      </div>
    </div>
  </header>
</template>