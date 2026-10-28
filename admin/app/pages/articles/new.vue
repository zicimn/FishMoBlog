<script setup lang="ts">
import { ApiError, describeError } from '~/composables/useApi'

const api = useApi()
const toast = useToast()

const submitting = ref(false)
const errorMsg = ref('')
const formRef = ref<{ commitUploads: () => void; rollbackUploads: () => Promise<void> } | null>(null)

async function onSubmit(payload: Record<string, unknown>) {
  submitting.value = true
  errorMsg.value = ''
  try {
    // 后端 Save 现在会回带新建文章的 id（services/article.py 的改动）
    const data = await api.post<{ id: number } | null>('/admin/article/save', payload)
    // 文章已入库，正文/封面里的图此刻才真正被引用 → 允许释放本地占位与预览
    formRef.value?.commitUploads()
    toast.ok('创建成功')
    if (data?.id) await navigateTo(`/articles/${data.id}/edit`)
    else await navigateTo('/articles')
  } catch (err) {
    // 保存失败（最常见的 409：slug 撞车）→ 把本次刚上传的图从云端删掉并还原表单。
    // 不做这一步的话，「改个 slug 再试」每试一次就在 Cloudinary 上多留一张孤儿图。
    await formRef.value?.rollbackUploads()
    // 后端 Save 现在会捕获 IntegrityError 并回 409（Conflict），不再是 500；
    // 409 的 detail 本身就是「该访问路径已被占用，请换一个」，这里换成更直白的落地文案。
    if (err instanceof ApiError && err.status === 409) {
      errorMsg.value = '创建失败：访问路径（slug）已被占用，换一个再试。'
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
      <h1 class="mt-2 text-xl font-semibold tracking-tight text-slate-900">写新文章</h1>
      <p class="mt-1 text-sm text-slate-500">
        默认存为草稿；确认无误后把状态改成「正常」，前台才会看到。
      </p>
    </header>

    <p v-if="errorMsg" class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {{ errorMsg }}
    </p>

    <ArticleForm ref="formRef" mode="create" :submitting="submitting" @submit="onSubmit" />
  </div>
</template>