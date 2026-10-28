<template>
  <!-- 登录页布局：单列居中，不做侧栏，避免未登录就暴露后台结构 -->
  <div class="min-h-screen flex items-center justify-center px-6 py-12 bg-slate-100">
    <div class="w-full max-w-sm">
      <slot />
    </div>
  </div>
</template>