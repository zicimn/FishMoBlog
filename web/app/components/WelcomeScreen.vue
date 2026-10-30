<script setup lang="ts">
// 首次进入站点的欢迎画面：移植自 Kirameku 的 components/layout/WelcomeScreen.tsx。
//
// 原版行为：
//   - 每个浏览器会话只出现一次（sessionStorage），不是路由切换动画；
//   - 全屏 slate-950 + 20% 透明度的模糊背景图；
//   - 「欢迎来到」→ 站名 → 时间问候 → 装饰线，逐级淡入；
//   - 3500ms 后整体淡出（背景同时轻微放大）。
//
// 这里是 Vue 版，不引 framer-motion：入场用 CSS animation 的 delay 错峰，
// 离场用 <Transition> 的 leave 阶段。纯客户端：SSR 不渲染，避免水合不一致。
const SESSION_KEY = 'fishmo_welcome_shown'
const VISIBLE_MS = 3500

const show = ref(false)
const greeting = ref('')
let timer: ReturnType<typeof setTimeout> | null = null

function getTimeGreeting() {
  const now = new Date()
  const h = now.getHours()
  const period =
    h < 6 ? '凌晨' : h < 9 ? '早上' : h < 12 ? '上午' : h < 14 ? '中午' : h < 18 ? '下午' : '晚上'
  // 0 点按 12 点算，避免出现「凌晨 0 点」
  const hour = h % 12 || 12
  const min = now.getMinutes()
  return `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日${period}${hour}点${min > 0 ? `${min}分` : ''}，很高兴与你相遇`
}

function finish() {
  if (timer) {
    clearTimeout(timer)
    timer = null
  }
  window.removeEventListener('keydown', onKeydown)
  show.value = false
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') finish()
}

onMounted(() => {
  let seen = ''
  try {
    seen = sessionStorage.getItem(SESSION_KEY) ?? ''
  } catch {
    // 隐私模式下 sessionStorage 可能不可用：当作没看过，本次照常展示
  }
  if (seen) return

  try {
    sessionStorage.setItem(SESSION_KEY, '1')
  } catch {
    // 写不进去的影响只是「刷新后会再看到一次」，不值得打断首屏
  }

  greeting.value = getTimeGreeting()
  show.value = true
  timer = setTimeout(finish, VISIBLE_MS)
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Transition name="welcome">
    <div
      v-if="show"
      class="welcome-root fixed inset-0 z-[200] flex items-center justify-center overflow-hidden"
      role="status"
      aria-label="欢迎"
      @click="finish"
    >
      <div class="welcome-bg absolute inset-0 bg-slate-950" />
      <div class="welcome-photo absolute inset-0" aria-hidden="true" />

      <div class="relative z-10 px-6 text-center">
        <p class="welcome-l1 text-base tracking-[0.3em] text-white/40 sm:text-lg">欢迎来到</p>

        <div class="welcome-l2 mt-4 flex items-center justify-center gap-1">
          <span class="text-4xl font-semibold tracking-tight text-white sm:text-5xl">Fishmo</span>
          <span class="text-4xl font-semibold text-sky-400 sm:text-5xl">の</span>
          <span class="text-4xl font-semibold tracking-tight text-white sm:text-5xl">博客</span>
        </div>

        <p class="welcome-l3 mt-4 text-xs tracking-wider text-white/40 sm:text-sm">
          {{ greeting }}
        </p>

        <div
          class="welcome-l4 mx-auto mt-8 h-px bg-gradient-to-r from-transparent via-sky-400/50 to-transparent"
          aria-hidden="true"
        />
      </div>

      <p
        class="welcome-skip absolute inset-x-0 bottom-8 text-center text-[10px] tracking-[0.2em] text-white/20"
      >
        点击任意处跳过
      </p>
    </div>
  </Transition>
</template>

<style scoped>
.welcome-bg,
.welcome-photo {
  transition: transform 0.8s ease-in-out;
}

.welcome-photo {
  background-image: url('/background.jpg');
  background-position: center;
  background-size: cover;
  filter: blur(20px);
  opacity: 0;
  animation: welcome-photo 1.2s ease-out both;
}

/* 与原版一致：文字错峰入场 */
.welcome-l1 {
  opacity: 0;
  animation: welcome-rise 0.6s ease-out 0.3s both;
}

.welcome-l2 {
  opacity: 0;
  animation: welcome-pop 0.7s cubic-bezier(0.22, 0.68, 0.32, 1) 0.8s both;
}

.welcome-l3 {
  opacity: 0;
  animation: welcome-rise 0.6s ease-out 1.5s both;
}

.welcome-l4 {
  width: 0;
  opacity: 0;
  animation: welcome-stretch 0.6s ease-out 2.2s both;
}

.welcome-skip {
  opacity: 0;
  animation: welcome-rise 0.6s ease-out 1.8s both;
}

/* 离场：整体淡出，深色底同时轻微放大（对应原版 exit scale 1.1） */
.welcome-leave-active {
  transition: opacity 0.8s ease-in-out;
}

.welcome-leave-to {
  opacity: 0;
}

.welcome-leave-active .welcome-bg {
  transform: scale(1.1);
}

@keyframes welcome-rise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes welcome-pop {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes welcome-stretch {
  from {
    width: 0;
    opacity: 0;
  }
  to {
    width: 10rem;
    opacity: 1;
  }
}

@keyframes welcome-photo {
  from {
    opacity: 0;
    transform: scale(1.2);
  }
  to {
    opacity: 0.2;
    transform: scale(1);
  }
}

/* 尊重系统「减少动态效果」：直接呈现最终状态，只保留定时淡出 */
@media (prefers-reduced-motion: reduce) {
  .welcome-photo {
    animation: none;
    opacity: 0.2;
    transform: none;
  }

  .welcome-l1,
  .welcome-l2,
  .welcome-l3,
  .welcome-skip {
    animation: none;
    opacity: 1;
    transform: none;
  }

  .welcome-l4 {
    animation: none;
    width: 10rem;
    opacity: 1;
  }

  .welcome-leave-active,
  .welcome-bg,
  .welcome-photo {
    transition: none;
  }
}
</style>