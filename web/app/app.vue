<template>
  <div class="relative min-h-screen">
    <!--
      全屏背景：public/background.jpg + 三层遮罩。
      玻璃卡片需要「背后有东西可透」，所以背景图必须固定铺满整屏，
      再压一层暗色保证文字对比度。
    -->
    <div class="fixed inset-0 -z-10 overflow-hidden">
      <img src="/background.jpg" alt="" class="h-full w-full scale-105 object-cover" />
      <div class="absolute inset-0 bg-slate-950/60" />
      <div class="absolute inset-0 bg-[radial-gradient(120%_80%_at_50%_-10%,rgba(56,189,248,0.18),transparent_55%)]" />
      <div class="absolute inset-0 bg-gradient-to-b from-slate-950/10 via-transparent to-slate-950/80" />
    </div>

    <NuxtPage />
  </div>
</template>