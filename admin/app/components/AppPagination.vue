<script setup lang="ts">
const props = defineProps<{ page: number; size: number; total: number }>()
const emit = defineEmits<{ (e: 'update:page', value: number): void }>()

const pages = computed(() => Math.max(1, Math.ceil(props.total / props.size)))
const canPrev = computed(() => props.page > 1)
const canNext = computed(() => props.page < pages.value)

function go(target: number) {
  if (target < 1 || target > pages.value || target === props.page) return
  emit('update:page', target)
}
</script>

<template>
  <div class="flex items-center justify-between gap-4">
    <p class="text-xs text-slate-500">
      共 {{ total }} 条 · 第 {{ page }} / {{ pages }} 页
    </p>
    <div class="flex items-center gap-2">
      <button
        class="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700
               hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        :disabled="!canPrev"
        @click="go(page - 1)"
      >
        上一页
      </button>
      <button
        class="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700
               hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        :disabled="!canNext"
        @click="go(page + 1)"
      >
        下一页
      </button>
    </div>
  </div>
</template>