<script setup lang="ts">
import { MAX_IMAGE_BYTES, useImageUpload } from '~/composables/useImageUpload'

export type ArticleDraft = {
  title: string
  path: string
  description: string
  cover: string
  cover_public_id: string
  status: number
  category_name: string
  content: string
}

const props = withDefaults(
  defineProps<{
    initial?: Partial<ArticleDraft> | null
    mode?: 'create' | 'edit'
    submitting?: boolean
  }>(),
  { initial: null, mode: 'create', submitting: false },
)

const emit = defineEmits<{ (e: 'submit', payload: Record<string, unknown>): void }>()

const form = reactive<ArticleDraft>({
  title: '',
  path: '',
  description: '',
  cover: '',
  cover_public_id: '',
  // 新建默认给「草稿」：管理端最怕的是手滑把半成品发出去，
  // 想发布就显式在下拉里选「正常」。
  status: 3,
  category_name: '',
  content: '',
})

const errors = reactive<Record<string, string>>({})

// 编辑页回填：后端 to_admin_detail 给的就是这些键。cover / cover_public_id 是
// 这轮为封面功能补上的 —— 之前详情接口不返回封面，编辑页每次保存都会把封面覆盖掉。
watch(
  () => props.initial,
  (v) => {
    if (!v) return
    form.title = v.title ?? ''
    form.path = v.path ?? ''
    form.description = v.description ?? ''
    form.cover = v.cover ?? ''
    form.cover_public_id = v.cover_public_id ?? ''
    form.status = typeof v.status === 'number' ? v.status : 3
    form.category_name = v.category_name ?? ''
    form.content = v.content ?? ''
  },
  { immediate: true },
)

// ---------- 封面：选图 → 本地预览 → 提交时才上传 ----------
// 与正文插图同一套语义：选中的文件先留在内存里，点「创建/保存」时才真正上传。
// 这样「选了图又放弃编辑」不会在 Cloudinary 上留下孤儿图。
const { error: uploadError, upload, remove } = useImageUpload()
const coverInput = ref<HTMLInputElement | null>(null)
const pendingCoverFile = ref<File | null>(null)
const coverPreviewUrl = ref('')
// 本次提交上传的封面：留着是为了「文章保存失败 → 回滚」（见 rollbackUploads）
let uploadedCover: { url: string; public_id: string } | null = null
// 选图**之前**的封面值：回滚时还原成它，否则表单会显示一个已被删掉的地址
let coverSnapshot: { cover: string; pid: string } = { cover: '', pid: '' }

// 预览优先用待上传的本地文件，其次才是已保存的（云图或外链）地址
const coverPreviewSrc = computed(() => coverPreviewUrl.value || form.cover)

// ---------- 预览：基于当前表单状态，不触发任何上传 ----------
// 新建页与编辑页共用这一处入口。未保存的正文/封面可能还是 blob: 本地地址，
// 在同一浏览器会话内可以直接渲染；这里刻意不复用提交逻辑 —— 点预览不应产生
// 上传、commitUploads 或 rollbackUploads 中的任何一种副作用。
const previewOpen = ref(false)
const previewArticle = computed(() => ({
  title: form.title,
  path: form.path,
  description: form.description,
  content: form.content,
  // 选过新封面时 form.cover 已被清空，必须用 coverPreviewSrc 才能看到本地预览图
  cover: coverPreviewSrc.value,
  status: form.status,
  category_name: form.category_name,
}))

function pickCover() {
  coverInput.value?.click()
}

function onCoverPicked(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  // 立即复位：不清空的话，连续选同一个文件不会再触发 change 事件
  input.value = ''
  if (!file) return

  uploadError.value = ''
  if (!file.type.startsWith('image/')) {
    uploadError.value = '只能上传图片文件'
    return
  }
  // 前端这道只是为了省一次注定失败的上传：真正的上限在服务端
  // （解压前 5MB + 像素上限，见 app/utils/cloudinary.py）
  if (file.size > MAX_IMAGE_BYTES) {
    uploadError.value = '图片超过 5MB，请先压缩后再上传'
    return
  }

  if (coverPreviewUrl.value) URL.revokeObjectURL(coverPreviewUrl.value)
  // 快照只在「本次待上传的第一张图」时记：保存失败要还原成选图**之前**的值。
  // 必须在下面清空 form.cover 之前取，且不能每次换图都覆盖 —— 否则连选两张时，
  // 第二张的快照会是第一张留下的 ''，回滚就还原不出原来那张云图地址了。
  if (!pendingCoverFile.value) {
    coverSnapshot = { cover: form.cover, pid: form.cover_public_id }
  }
  pendingCoverFile.value = file
  coverPreviewUrl.value = URL.createObjectURL(file)
  // 已选定本地文件：清掉旧的 url / public_id，避免旧值被当成最终结果提交
  form.cover = ''
  form.cover_public_id = ''
}

function dropPendingCover() {
  if (coverPreviewUrl.value) URL.revokeObjectURL(coverPreviewUrl.value)
  coverPreviewUrl.value = ''
  pendingCoverFile.value = null
}

function clearCover() {
  // 只清本地引用。已保存过的那张云图由后端在保存成功时销毁
  // （services/article.py 的 Edit）；前端提前删掉的话，「清掉又改回来」就成裂图了。
  dropPendingCover()
  form.cover = ''
  form.cover_public_id = ''
}

// 手工粘贴外链即视为「不用这张待上传的本地图」
function onCoverUrlInput() {
  if (coverPreviewUrl.value && form.cover.trim()) dropPendingCover()
}

onBeforeUnmount(dropPendingCover)

// slug 规则与前端路由/path 列的用途保持一致：只允许 URL 里安全的字符。
// 后端 ArticleSaveRequest 对 path 没有校验（nullable=False/unique=True 在模型层），
// 这里先挡住空值与非法字符，避免白跑一次请求。
const SLUG_RE = /^[A-Za-z0-9_-]+$/

function validate(): boolean {
  errors.title = form.title.trim() ? '' : '标题必填'
  const p = form.path.trim()
  if (!p) errors.path = '访问路径必填（模型层为 NOT NULL + 唯一）'
  else if (!SLUG_RE.test(p)) errors.path = '只能包含字母、数字、连字符与下划线'
  else errors.path = ''
  errors.content = form.content && form.content !== '<p></p>' ? '' : '正文不能为空'
  return !Object.values(errors).some(Boolean)
}

// 提交期间的本地状态：上传图片发生在 emit 之前，这段空档 submitting 还是 false，
// 必须自己把按钮挡住，否则用户能连点两次造成重复上传。
const preparing = ref(false)
const editorRef = ref<{
  flushPendingImages: () => Promise<boolean>
  rollbackUploads: () => Promise<void>
  commitUploads: () => void
} | null>(null)

async function onSubmit() {
  if (!validate()) return

  preparing.value = true
  try {
    // 1) 正文里的占位图（blob: 本地预览）先上传并替换成真 URL。
    //    返回 false 表示有图没传成功（编辑器内部已把已传的那几张一并回滚），
    //    必须中断提交 —— 否则就把 blob: 写进库了。
    const flushed = await editorRef.value?.flushPendingImages()
    if (flushed === false) {
      errors.content = '正文里的图片没能上传成功，请重试后再保存'
      return
    }

    // 2) 封面文件此刻才上传（选图阶段只做本地预览）
    if (pendingCoverFile.value) {
      const uploaded = await upload(pendingCoverFile.value)
      if (!uploaded) return // 失败原因已写进 uploadError
      form.cover = uploaded.url
      form.cover_public_id = uploaded.public_id
      uploadedCover = uploaded
      // 这里**不调** dropPendingCover()：本地文件与预览要留到「文章保存成功」为止，
      // 否则保存失败就没法回滚重传（见 rollbackUploads / commitUploads）。
    }

    const title = form.title.trim()
    const path = form.path.trim()
    const description = form.description.trim()
    const cover = form.cover.trim()
    const category_name = form.category_name.trim()

    if (props.mode === 'create') {
      // 新建走 ArticleSaveRequest：description / content / category_name 是必填字符串，
      // 空串在 Pydantic 层合法；cover 已改为可选，空串由后端统一归一成 NULL。
      emit('submit', {
        title,
        path,
        status: form.status,
        description,
        cover,
        cover_public_id: form.cover_public_id,
        content: form.content,
        category_name,
      })
      return
    }

    // 编辑走 ArticleEditRequest：后端已改为按「键是否出现在请求体里」判断
    // （Pydantic v2 的 model_fields_set），语义是：发 null = 清空，不发这个键 = 保持原值。
    // 这里对可空字段一律「发键 + 值为 null 或新值」，让「表单显示什么，库里就是什么」成立。
    // title / path / content 是 NOT NULL 列，留空只会被后端忽略，故原样带着。
    const payload: Record<string, unknown> = {
      title,
      path,
      status: form.status,
      content: form.content,
      description: description || null,
      cover: cover || null,
      // 手动粘贴外链时 cover_public_id 为空 → 发 null 清掉旧值，
      // 后端据此把云端旧图销毁（services/article.py 的 Edit）。
      cover_public_id: form.cover_public_id || null,
    }
    // 分类名留空 = 不修改：详情接口只回 category_id 不回名字，编辑页这一栏本来就是空的。
    if (category_name) payload.category_name = category_name

    emit('submit', payload)
  } finally {
    preparing.value = false
  }
}

/**
 * 文章**保存成功**后由页面调用：云端图已被正文引用，清掉本地占位与预览。
 * 页面必须在请求成功之后调用 —— 提前调等于扔掉保存失败时唯一的还原依据。
 */
function commitUploads() {
  editorRef.value?.commitUploads()
  uploadedCover = null
  coverSnapshot = { cover: '', pid: '' }
  dropPendingCover()
}

/**
 * 文章**保存失败**后由页面调用：把本次已上传的图从云端删掉，并还原表单与正文，
 * 让「重试保存」从干净状态重新上传。否则封面已传但保存撞 409 时，用户每改一次
 * slug 重试就会在 Cloudinary 上多留一张没人引用的图。
 */
async function rollbackUploads() {
  await editorRef.value?.rollbackUploads()
  if (uploadedCover) {
    await remove(uploadedCover.public_id)
    // 还原成上传前的值：库里没变，表单也不该显示一个已被删掉的地址
    form.cover = coverSnapshot.cover
    form.cover_public_id = coverSnapshot.pid
    uploadedCover = null
  }
}

// 页面的契约：请求成功 → commitUploads()；请求失败 → await rollbackUploads()
defineExpose({ commitUploads, rollbackUploads })
</script>

<template>
  <form class="space-y-6" @submit.prevent="onSubmit">
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- 主列 -->
      <div class="lg:col-span-2 space-y-5">
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1.5">标题 <span class="text-rose-500">*</span></label>
          <input
            v-model="form.title"
            maxlength="255"
            placeholder="给文章起个标题"
            class="w-full rounded-lg border px-3.5 py-2.5 text-sm outline-none transition-colors
                   focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
            :class="errors.title ? 'border-rose-300' : 'border-slate-200'"
          >
          <p v-if="errors.title" class="mt-1 text-xs text-rose-600">{{ errors.title }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1.5">访问路径（slug） <span class="text-rose-500">*</span></label>
          <div class="flex items-center gap-2">
            <span class="text-xs text-slate-400 shrink-0">/article/</span>
            <input
              v-model="form.path"
              maxlength="255"
              placeholder="my-first-post"
              class="w-full rounded-lg border px-3.5 py-2.5 text-sm font-mono outline-none transition-colors
                     focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
              :class="errors.path ? 'border-rose-300' : 'border-slate-200'"
            >
          </div>
          <p v-if="errors.path" class="mt-1 text-xs text-rose-600">{{ errors.path }}</p>
          <p v-else class="mt-1 text-xs text-slate-400">模型层是 NOT NULL + 唯一索引，重复会返回 409</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1.5">正文 <span class="text-rose-500">*</span></label>
          <RichTextEditor ref="editorRef" v-model="form.content" />
          <p v-if="errors.content" class="mt-1 text-xs text-rose-600">{{ errors.content }}</p>
        </div>
      </div>

      <!-- 侧列 -->
      <div class="space-y-5">
        <div class="rounded-xl border border-slate-200 bg-white p-5 space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1.5">状态</label>
            <select
              v-model.number="form.status"
              class="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none
                     focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
            >
              <option :value="1">正常（对外可见）</option>
              <option :value="2">隐藏（仅后台可见）</option>
              <option :value="3">草稿（仅后台可见）</option>
            </select>
            <p class="mt-1 text-xs text-slate-400">
              对外可见只有「正常」；隐藏与草稿前台一律 404。
            </p>
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1.5">分类</label>
            <input
              v-model="form.category_name"
              maxlength="50"
              placeholder="如：后端"
              class="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none
                     focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
            >
            <p class="mt-1 text-xs text-slate-400">后端会自动建不存在的分类，无需先创建。</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1.5">摘要</label>
            <textarea
              v-model="form.description"
              rows="3"
              maxlength="500"
              placeholder="列表页展示的简介"
              class="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none resize-y
                     focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1.5">封面图</label>
            <div class="flex gap-2">
              <input
                v-model="form.cover"
                maxlength="500"
                placeholder="https://..."
                class="w-full rounded-lg border border-slate-200 px-3.5 py-2.5 text-sm outline-none
                       focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
                @input="onCoverUrlInput"
              >
              <button
                type="button"
                class="shrink-0 rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-700
                       hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                :disabled="preparing || submitting"
                @click="pickCover"
              >
                选择图片
              </button>
            </div>
            <input ref="coverInput" type="file" accept="image/*" class="hidden" @change="onCoverPicked">
            <p v-if="uploadError" class="mt-1 text-xs text-rose-600">{{ uploadError }}</p>
            <p v-else class="mt-1 text-xs text-slate-400">
              选好图后点「{{ mode === 'create' ? '创建文章' : '保存修改' }}」时才会上传
              （服务端转 WEBP 存 Cloudinary，单张 ≤ 5MB）；也可以直接粘贴外链。
            </p>
            <div v-if="coverPreviewSrc" class="mt-2 space-y-1.5">
              <img
                :src="coverPreviewSrc"
                alt="封面预览"
                class="h-28 w-full object-cover rounded-lg border border-slate-200"
              >
              <div class="flex items-center gap-2">
                <span v-if="pendingCoverFile" class="text-xs text-amber-600">已选新图，保存时上传</span>
                <button
                  type="button"
                  class="text-xs text-slate-500 hover:text-rose-600 transition-colors"
                  @click="clearCover"
                >
                  清除封面
                </button>
              </div>
            </div>
          </div>
        </div>

        <div
          v-if="mode === 'edit'"
          class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600 leading-relaxed"
        >
          <strong class="font-semibold">编辑语义：</strong>
          摘要与封面按表单内容整体覆盖 —— 清空表单里的摘要/封面并保存，库里也会被清空
          （旧封面图会一并从 Cloudinary 删除）。正文里的新插图与封面都是**点保存时才上传**，
          没保存就离开页面不会在云端留下任何图片。标题、访问路径、正文是 NOT NULL 字段，留空视为「不修改」。
        </div>

        <div class="space-y-2">
          <button
            type="button"
            class="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium
                   text-slate-700 hover:bg-slate-50 transition-colors"
            @click="previewOpen = true"
          >
            预览当前内容
          </button>
          <button
            type="submit"
            :disabled="submitting || preparing"
            class="w-full rounded-lg bg-slate-900 px-4 py-3 text-sm font-medium text-white
                   hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {{ submitting || preparing ? '提交中…' : mode === 'create' ? '创建文章' : '保存修改' }}
          </button>
          <p class="text-[11px] leading-relaxed text-slate-400">
            预览只读取当前表单，不会上传图片，也不会保存。
          </p>
        </div>
      </div>
    </div>

    <!-- 未保存态预览：数据直接来自上面的 form，不走接口 -->
    <ArticlePreview :open="previewOpen" :article="previewArticle" @close="previewOpen = false" />
  </form>
</template>
