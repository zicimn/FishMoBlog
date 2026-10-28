<script setup lang="ts">
withDefaults(defineProps<{ subtitle?: string }>(), {
  subtitle: '写点东西，留给时间',
})
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
      <span class="hidden text-xs text-white/40 sm:block">{{ subtitle }}</span>
    </div>
  </header>
</template>