<script setup lang="ts">
import { EditorContent, useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
// 具名导入 Image 会遮蔽浏览器全局的 Image 构造函数，这里用默认导出并起别名。
// 注意 StarterKit 里并不含图片扩展（装的是 3.32），必须单独注册。
import ImageExtension from '@tiptap/extension-image'
import { MAX_IMAGE_BYTES, useImageUpload } from '~/composables/useImageUpload'

// 后端 article.content 存的是 HTML 字符串（models/article.py:36），
// 所以这里交给父组件的永远是可直提的 HTML，而不是 JSON 文档结构。
const model = defineModel<string>({ default: '' })
const showSource = ref(false)

// 插图走「提交时才上传」：选图后先插入 blob: 本地预览并打上 data-pending-upload 标记，
// 真正点保存时由 flushPendingImages() 统一上传、把 src 换成 Cloudinary 地址。
// 这样「插了图又放弃编辑」不会在云端留下孤儿图。
// 该属性必须声明进 schema（addAttributes）：ProseMirror 只保留 schema 里声明过的 attr，
// 不声明的话渲染出的 HTML 里就没有标记，flush 时就定位不到占位图了。
const PendingImage = ImageExtension.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      'data-pending-upload': {
        default: null,
        parseHTML: (el: HTMLElement) => el.getAttribute('data-pending-upload'),
        renderHTML: (attrs: Record<string, unknown>) =>
          attrs['data-pending-upload'] ? { 'data-pending-upload': attrs['data-pending-upload'] } : {},
      },
    }
  },
})

// 正文插图与文章封面共用同一套上传链路（base64 → 后端转 WEBP → Cloudinary）
const { uploading, error: uploadError, upload, remove } = useImageUpload()
const imageInput = ref<HTMLInputElement | null>(null)

type PendingEntry = {
  file: File
  previewUrl: string
  // 上传成功后就地记下云端坐标，但**不从 Map 里删掉**：文章保存失败时要靠它把文档里的
  // 真实 URL 还原成占位图、把文件放回待上传队列（重传会拿到新的 public_id，旧的删掉）。
  uploaded: { publicId: string; url: string } | null
}
// 非响应式 Map：只在 pick / flush / rollback 时遍历，不需要驱动渲染；数量另用 ref 给工具栏用
const pending = new Map<string, PendingEntry>()
const pendingCount = ref(0)

// 工具栏角标只数「还没上传的」：上传过但尚未随文章入库的不该再算待上传，
// 否则回滚一次数量就虚高。
function refreshPendingCount() {
  let n = 0
  for (const item of pending.values()) if (!item.uploaded) n += 1
  pendingCount.value = n
}

function pickImage() {
  imageInput.value?.click()
}

function onImagePicked(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  // 立即复位：不清空的话，连续选同一个文件不会再触发 change
  input.value = ''
  if (!file) return

  uploadError.value = ''
  if (!file.type.startsWith('image/')) {
    uploadError.value = '只能插入图片文件'
    return
  }
  // 与封面同一套限额：真正的上限在服务端（解压前 5MB + 25M 像素）
  if (file.size > MAX_IMAGE_BYTES) {
    uploadError.value = '图片超过 5MB，请先压缩后再插入'
    return
  }

  const key = `p${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`
  const previewUrl = URL.createObjectURL(file)
  pending.set(key, { file, previewUrl, uploaded: null })
  refreshPendingCount()

  // 用 insertContent 而不是 setImage：需要多带一个自定义属性，
  // 而 setImage 的参数类型只声明了 src/alt/title。
  editor.value?.chain().focus().insertContent({
    type: 'image',
    attrs: { src: previewUrl, alt: file.name, 'data-pending-upload': key },
  }).run()
}

function dropPending(key: string) {
  const item = pending.get(key)
  if (!item) return
  URL.revokeObjectURL(item.previewUrl)
  pending.delete(key)
  refreshPendingCount()
}

function collectSlots(instance: NonNullable<typeof editor.value>) {
  // 一次遍历收集所有占位图的位置。setNodeMarkup 不改变节点尺寸，
  // 因此这些位置在同一个 tr 上始终有效，可以合并成一次 dispatch。
  const slots = new Map<string, number[]>()
  instance.state.doc.descendants((node, pos) => {
    const key = node.attrs['data-pending-upload']
    if (node.type.name === 'image' && key) {
      const arr = slots.get(key) ?? []
      arr.push(pos)
      slots.set(key, arr)
    }
    return true
  })
  return slots
}

/**
 * 把所有占位图上传成真 URL 并替换。
 * 返回 false = 有图片没传成功，调用方必须中断提交（避免把 blob: 地址存进库）。
 * 只上传**仍存在于文档里**的占位图：用户若在源码视图里删掉了它们，就说明不再需要，
 * 连上传都不做，自然也不会产生孤儿图。
 */
async function flushPendingImages(): Promise<boolean> {
  const instance = editor.value
  if (!instance) return true

  const todo = Array.from(pending.entries()).filter(([, item]) => !item.uploaded)
  if (todo.length === 0) return true

  const slots = collectSlots(instance)

  for (const [key, item] of todo) {
    const positions = slots.get(key)
    if (!positions?.length) {
      // 用户把这张占位图从正文里删掉了：不再需要，连上传都不做
      dropPending(key)
      continue
    }

    const res = await upload(item.file)
    if (!res) {
      // 前面已传成功的那些一并回滚：否则「半上传」状态下用户若放弃提交，
      // 已传的图就成了没人引用的孤儿。回滚会把文档还原成占位图，
      // 用户重试时统一重传。
      await rollbackUploads()
      return false
    }

    item.uploaded = { publicId: res.public_id, url: res.url }
    refreshPendingCount()

    const tr = instance.state.tr
    for (const pos of positions) {
      const node = tr.doc.nodeAt(pos)
      if (node) {
        tr.setNodeMarkup(pos, undefined, {
          ...node.attrs,
          src: res.url,
          // 标记必须清掉：留着它既会让后端防漏闸误判，也会让下一次 flush 重复认领
          'data-pending-upload': null,
        })
      }
    }
    instance.view.dispatch(tr)
  }

  // dispatch 会触发 onUpdate 回写 model；这里再显式同步一次，
  // 保证调用方「await flush 之后立刻读 form.content」也能拿到替换后的 HTML。
  model.value = instance.getHTML()
  return true
}

/**
 * 回滚本次已上传的图，用于「文章保存失败」。
 *
 * 三件事缺一不可：删掉云端刚传的图、把正文里的 URL 还原成 blob 占位并重新打上标记、
 * 把文件放回待上传队列（重传会拿到新的 public_id）。只删云端不还原文档的话，
 * 用户重试时正文里就是一个已失效的 URL（而 flush 也不会再传它）。
 */
async function rollbackUploads() {
  const instance = editor.value
  const targets = Array.from(pending.entries()).filter(([, item]) => item.uploaded)
  if (targets.length === 0) return

  for (const [key, item] of targets) {
    const up = item.uploaded
    if (!up) continue

    if (instance) {
      const tr = instance.state.tr
      instance.state.doc.descendants((node, pos) => {
        if (node.type.name === 'image' && node.attrs.src === up.url) {
          tr.setNodeMarkup(pos, undefined, {
            ...node.attrs,
            src: item.previewUrl,
            'data-pending-upload': key,
          })
        }
        return true
      })
      if (tr.docChanged) instance.view.dispatch(tr)
    }

    // remove() 内部吞异常：回滚是尽力而为，删不掉最多留一张孤儿图，
    // 不能反过来把用户的编辑页带崩。
    await remove(up.publicId)
    item.uploaded = null
  }

  refreshPendingCount()
  if (instance) model.value = instance.getHTML()
}

/**
 * 文章已成功入库：云端图已被正文引用，本地占位可以彻底释放。
 * 必须在父组件的请求成功后调用 —— 提前调用等于把「保存失败时唯一的还原依据」扔掉。
 */
function commitUploads() {
  for (const key of Array.from(pending.keys())) dropPending(key)
}

// 父组件（ArticleForm）的契约：提交前 await flushPendingImages()；
// 请求成功后 commitUploads()；请求失败后 await rollbackUploads()。
defineExpose({ flushPendingImages, rollbackUploads, commitUploads })

const editor = useEditor({
  content: model.value || '',
  // allowBase64:false 是刻意的：正文以 HTML 存库（models/article.py 的 content），
  // 放行 data:URI 会让正文体积凭空涨三分之一且无法清理，约定只用上传后的 URL。
  extensions: [
    StarterKit,
    PendingImage.configure({
      inline: false,
      allowBase64: false,
      // 拖拽下侧两角调整尺寸。Tiptap 松手时把 px 宽高写回节点的 width/height 属性
      // （Image 扩展的 schema 本来就声明了它们），所以尺寸会随 HTML 一起入库；
      // 前台用 max-width:100%; height:auto 兜住窄屏，不会撑破布局。
      // 手柄本身是裸 div，必须靠 main.css 里的 [data-resize-handle] 样式才看得见。
      resize: {
        enabled: true,
        directions: ['bottom-right', 'bottom-left'],
        minWidth: 80,
        alwaysPreserveAspectRatio: true,
      },
    }),
  ],
  onUpdate: ({ editor }) => {
    model.value = editor.getHTML()
  },
})

// 编辑页是异步拉详情再回填的：外部值变化要推进编辑器。
// 必须比较一次 getHTML，否则父组件每次回写都会触发 setContent → 光标跳到开头。
watch(model, (value) => {
  const instance = editor.value
  if (!instance) return
  if (value === instance.getHTML()) return
  // emitUpdate:false 是关键，避免把这次程序化写入当成用户编辑再回写一遍
  instance.commands.setContent(value || '', { emitUpdate: false })
})

onBeforeUnmount(() => {
  // 离开页面：释放本地预览 URL。注意这里**不删云端**已上传的图 ——
  // 保存成功的那批已被正文引用；保存失败的那批由父组件的 rollbackUploads 负责清理。
  for (const key of Array.from(pending.keys())) dropPending(key)
  editor.value?.destroy()
})

const tools = [
  { label: 'B', title: '加粗', act: 'bold' },
  { label: 'I', title: '斜体', act: 'italic' },
  { label: 'H2', title: '二级标题', act: 'heading2' },
  { label: 'H3', title: '三级标题', act: 'heading3' },
  { label: '• 列表', title: '无序列表', act: 'bulletList' },
  { label: '1. 列表', title: '有序列表', act: 'orderedList' },
  { label: '引用', title: '引用块', act: 'blockquote' },
  { label: '代码块', title: '代码块', act: 'codeBlock' },
] as const

function toggle(act: string) {
  const c = editor.value?.chain().focus()
  if (!c) return
  if (act === 'bold') c.toggleBold().run()
  else if (act === 'italic') c.toggleItalic().run()
  else if (act === 'heading2') c.toggleHeading({ level: 2 }).run()
  else if (act === 'heading3') c.toggleHeading({ level: 3 }).run()
  else if (act === 'bulletList') c.toggleBulletList().run()
  else if (act === 'orderedList') c.toggleOrderedList().run()
  else if (act === 'blockquote') c.toggleBlockquote().run()
  else if (act === 'codeBlock') c.toggleCodeBlock().run()
}

function isOn(act: string) {
  const e = editor.value
  if (!e) return false
  if (act === 'heading2') return e.isActive('heading', { level: 2 })
  if (act === 'heading3') return e.isActive('heading', { level: 3 })
  return e.isActive(act)
}
</script>

<template>
  <div class="rounded-xl border border-slate-200 bg-white overflow-hidden">
    <div class="flex flex-wrap items-center gap-1 border-b border-slate-200 bg-slate-50 px-2 py-2">
      <button
        v-for="t in tools"
        :key="t.act"
        type="button"
        :title="t.title"
        class="rounded-md px-2.5 py-1 text-xs transition-colors"
        :class="isOn(t.act)
          ? 'bg-slate-900 text-white'
          : 'text-slate-600 hover:bg-slate-200/70'"
        @click="toggle(t.act)"
      >
        {{ t.label }}
      </button>

      <button
        type="button"
        title="插入图片（保存时统一上传到 Cloudinary）"
        class="rounded-md px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-200/70 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        :disabled="uploading || !editor"
        @click="pickImage"
      >
        {{ uploading ? '上传中…' : '插图' }}
      </button>
      <span
        v-if="pendingCount"
        class="px-1 text-[11px] text-amber-600"
        title="这些图会在保存时统一上传，放弃编辑不会留在云端"
      >
        {{ pendingCount }} 张待上传
      </span>
      <input ref="imageInput" type="file" accept="image/*" class="hidden" @change="onImagePicked">

      <span class="mx-1 h-4 w-px bg-slate-300" />

      <button
        type="button"
        class="rounded-md px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-200/70 transition-colors disabled:opacity-40"
        :disabled="!editor?.can().undo()"
        @click="editor?.chain().focus().undo().run()"
      >
        撤销
      </button>
      <button
        type="button"
        class="rounded-md px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-200/70 transition-colors disabled:opacity-40"
        :disabled="!editor?.can().redo()"
        @click="editor?.chain().focus().redo().run()"
      >
        重做
      </button>

      <button
        type="button"
        class="ml-auto rounded-md px-2.5 py-1 text-xs transition-colors"
        :class="showSource ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-200/70'"
        @click="showSource = !showSource"
      >
        {{ showSource ? '回到富文本' : '看 HTML 源码' }}
      </button>
    </div>

    <p v-if="uploadError" class="border-t border-rose-100 bg-rose-50 px-3 py-2 text-xs text-rose-700">
      {{ uploadError }}
    </p>

    <!-- 源码视图：正文最终就是 HTML，能直接改源码对排错很有用 -->
    <textarea
      v-if="showSource"
      v-model="model"
      spellcheck="false"
      class="w-full min-h-[22rem] p-4 font-mono text-xs leading-relaxed text-slate-700 outline-none resize-y"
    />
    <div v-else class="tiptap-editor">
      <EditorContent :editor="editor" />
    </div>
  </div>
</template>