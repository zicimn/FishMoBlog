<script setup lang="ts">
// 首页没有独立仪表盘：管理端目前只有文章管理一件事，
// 直接进列表比先落一个空壳概览页少一次点击。
await navigateTo('/articles', { replace: true })
</script>

<template>
  <div class="text-sm text-slate-500">正在跳转到文章列表…</div>
</template>