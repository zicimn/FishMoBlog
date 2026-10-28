<script setup lang="ts">
import { ApiError, describeError } from '~/composables/useApi'

const route = useRoute()
const api = useApi()
const toast = useToast()

const id = Number(route.params.id)

const initial = ref<Record<string, unknown> | null>(null)
const loading = ref(true)
const submitting = ref(false)
const errorMsg = ref('')
const formRef = ref<{ commitUploads: () => void; rollbackUploads: () => Promise<void> } | null>(null)

async function fetchOne() {
  // 走后台详情接口（后端已改为 GetId(id, status=True)），
  // 所以隐藏与草稿在这里都能读到、也能回填 status。
  return await api.get<Record<string, unknown>>(`/admin/article/${id}`)
}

onMounted(async () => {
  try {
    initial.value = await fetchOne()
  } catch (err) {
    errorMsg.value = describeError(err)
  } finally {
    loading.value = false
  }
})

async function onSubmit(payload: Record<string, unknown>) {
  submitting.value = true
  errorMsg.value = ''
  try {
    await api.put(`/admin/article/edit/${id}`, payload)
    // 保存成功：正文/封面里的图已被库里的记录引用，可以释放本地占位与预览了
    formRef.value?.commitUploads()
    toast.ok('已保存')
    // 重新拉一次而不是直接改本地态：以库里的结果为准才不会让界面撒谎
    // （换封面后后端会销毁旧图、空值语义也可能让某些字段保持原样）。
    initial.value = await fetchOne()
  } catch (err) {
    // 保存失败 → 删掉本次刚上传的图并还原表单/正文，避免重复重试堆孤儿图
    await formRef.value?.rollbackUploads()
    // 后端 Edit 现在捕获 IntegrityError 回 409，不再是 500。
    if (err instanceof ApiError && err.status === 409) {
      errorMsg.value = '保存失败：访问路径（slug）与其他文章冲突，换一个再试。'
    } else {
      errorMsg.value = describeError(err)
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <header>
      <NuxtLink to="/articles" class="text-xs text-slate-500 hover:text-slate-800">← 返回列表</NuxtLink>
      <h1 class="mt-2 text-xl font-semibold tracking-tight text-slate-900">编辑文章</h1>
      <p class="mt-1 text-sm text-slate-500">文章 ID：{{ id }}</p>
    </header>

    <p v-if="errorMsg" class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {{ errorMsg }}
    </p>

    <div v-if="loading" class="rounded-xl border border-slate-200 bg-white px-4 py-16 text-center text-sm text-slate-400">
      正在加载文章…
    </div>

    <template v-else-if="initial">
      <p class="rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-500 leading-relaxed">
        详情接口只返回 <code class="font-mono">category_id</code>，不返回分类名，
        所以「分类」一栏是空的 —— 保持留空即为不修改该字段。
      </p>
      <ArticleForm ref="formRef" mode="edit" :initial="initial" :submitting="submitting" @submit="onSubmit" />
    </template>
  </div>
</template>