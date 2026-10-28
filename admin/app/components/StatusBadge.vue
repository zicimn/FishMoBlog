<script setup lang="ts">
// 状态含义来自后端 models/article.py:13-15，不要自己发明第四种。
const props = defineProps<{ status: number }>()

const MAP: Record<number, { label: string; cls: string }> = {
  1: { label: '正常', cls: 'bg-emerald-50 text-emerald-700 ring-emerald-200' },
  2: { label: '隐藏', cls: 'bg-amber-50 text-amber-700 ring-amber-200' },
  3: { label: '草稿', cls: 'bg-slate-100 text-slate-600 ring-slate-200' },
}

const meta = computed(
  () => MAP[props.status] ?? { label: `未知(${props.status})`, cls: 'bg-rose-50 text-rose-700 ring-rose-200' },
)
</script>

<template>
  <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs ring-1 ring-inset" :class="meta.cls">
    {{ meta.label }}
  </span>
</template>