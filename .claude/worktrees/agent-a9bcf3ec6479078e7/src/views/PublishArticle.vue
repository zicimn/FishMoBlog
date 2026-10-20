<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { articleApi } from '@/api/article'
import { useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const router = useRouter()

const title = ref('')
const category = ref('ai')
const content = ref('')
const images = ref<string[]>([])
const error = ref('')
const success = ref('')
const loading = ref(false)
const showPreview = ref(false)

// Markdown 解析器
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
})

// 渲染后的 HTML
const renderedContent = computed(() => {
  if (!content.value) return ''
  const html = md.render(content.value)
  return DOMPurify.sanitize(html)
})

// 自动保存相关
const lastSavedTime = ref('')
const isSaving = ref(false)
let saveTimer: ReturnType<typeof setInterval> | null = null
const DRAFT_KEY = 'article_draft'

const categories = ['all', 'code', 'health', 'other', 'test', 'study']

// 加载草稿
const loadDraft = () => {
  try {
    const draft = localStorage.getItem(DRAFT_KEY)
    if (draft) {
      const data = JSON.parse(draft)
      title.value = data.title || ''
      category.value = data.category || 'ai'
      content.value = data.content || ''
      // 图片数据较大，不保存到 localStorage
      lastSavedTime.value = data.savedTime || ''
    }
  } catch (e) {
    console.error('Failed to load draft:', e)
  }
}

// 保存草稿
const saveDraft = async () => {
  if (loading.value) return
  
  // 只有有内容时才保存
  if (!title.value && !content.value) return
  
  isSaving.value = true
  try {
    const draft = {
      title: title.value,
      category: category.value,
      content: content.value,
      savedTime: new Date().toLocaleString()
    }
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))
    lastSavedTime.value = draft.savedTime
  } catch (e) {
    console.error('Failed to save draft:', e)
  } finally {
    isSaving.value = false
  }
}

// 清除草稿
const clearDraft = () => {
  localStorage.removeItem(DRAFT_KEY)
  lastSavedTime.value = ''
}

// 监听数据变化自动保存
watch([title, category, content], () => {
  saveDraft()
}, { deep: true })

// 定时保存（额外保障）
onMounted(() => {
  loadDraft()
  saveTimer = setInterval(saveDraft, 30000) // 每30秒自动保存
})

onUnmounted(() => {
  if (saveTimer) {
    clearInterval(saveTimer)
  }
})

const handlePublish = async () => {
  if (!title.value || !category.value || !content.value) {
    error.value = 'Please fill in all required fields'
    return
  }

  loading.value = true
  error.value = ''
  success.value = ''
  
  try {
    const response = await articleApi.publish({ title: title.value, category: category.value, content: content.value, images: images.value })
    success.value = 'Article published successfully!'
    // 发布成功后清除草稿
    clearDraft()
    // 跳转到文章详情页
    const articleId = response.data?.id
    setTimeout(() => {
      router.push(articleId ? `/article/${articleId}` : '/')
    }, 2000)
  } catch (err: unknown) {
    error.value = '发布文章失败，请重试。'
    console.error(err)
  } finally {
    loading.value = false
  }
}

const fileInput = ref<HTMLInputElement | null>(null)

const addImage = () => {
  if (fileInput.value) {
    fileInput.value.click()
  }
}

const handleFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const file = target.files[0]
    if (file) {
      // 限制单张图片大小为16MB
      if (file.size > 16 * 1024 * 1024) {
        error.value = '单张图片大小不能超过16MB'
        return
      }
      
      // 计算当前已上传图片的总大小
      const currentTotalSize = images.value.reduce((total, img) => total + img.length, 0)
      const newTotalSize = currentTotalSize + file.size
      
      // 限制所有图片总大小为16MB
      if (newTotalSize > 16 * 1024 * 1024) {
        error.value = '所有图片总大小不能超过16MB'
        return
      }
      
      const reader = new FileReader()
      reader.onload = (event) => {
        const result = event.target?.result as string
        images.value.push(result)
        error.value = '' // 清除错误信息
      }
      reader.readAsDataURL(file)
    }
  }
}

const removeImage = (index: number) => {
  images.value.splice(index, 1)
}

// Markdown 插入函数
const insertMarkdown = (prefix: string, suffix: string, placeholder: string) => {
  const textarea = document.getElementById('content') as HTMLTextAreaElement
  if (!textarea || loading.value) return
  
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const selectedText = content.value.substring(start, end)
  
  const newText = content.value.substring(0, start) + 
                  prefix + 
                  (selectedText || placeholder) + 
                  suffix + 
                  content.value.substring(end)
  
  content.value = newText
  
  // 设置光标位置
  setTimeout(() => {
    textarea.focus()
    const cursorPos = start + prefix.length + (selectedText ? selectedText.length : placeholder.length) + suffix.length
    textarea.setSelectionRange(cursorPos, cursorPos)
  }, 0)
}
</script>

<template>
  <div class="publish-page">
    <div class="publish-container">
      <div class="auto-save-bar">
        <span v-if="isSaving" class="save-status saving">
          <span class="spinner-ring" style="width:12px;height:12px;border-width:2px;display:inline-block;"></span>
          保存中...
        </span>
        <span v-else-if="lastSavedTime" class="save-status saved">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
          已自动保存 ({{ lastSavedTime }})
        </span>
      </div>

      <div class="page-heading">
        <h1 class="page-title">发布文章</h1>
        <p class="page-subtitle">分享您的想法，使用 Markdown 排版</p>
      </div>

      <form @submit.prevent="handlePublish" class="publish-form">
        <div class="form-card">
          <div class="form-group">
            <label for="title">标题</label>
            <input
              type="text"
              id="title"
              v-model="title"
              required
              :disabled="loading"
              class="input-field title-input"
              placeholder="输入文章标题..."
            />
          </div>
          <div class="form-group">
            <label for="category">分类</label>
            <div class="select-wrapper">
              <select
                id="category"
                v-model="category"
                required
                :disabled="loading"
              >
                <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
              </select>
            </div>
          </div>
        </div>

        <div class="form-card editor-card">
          <div class="editor-header">
            <label class="editor-label">内容 (支持 Markdown)</label>
            <div class="editor-actions">
              <button
                type="button"
                @click="showPreview = !showPreview"
                class="btn btn-ghost"
                :disabled="loading"
                style="font-size:0.8rem;padding:6px 14px;"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                {{ showPreview ? '编辑' : '预览' }}
              </button>
            </div>
          </div>

          <!-- Toolbar -->
          <div class="md-toolbar">
            <button type="button" @click="insertMarkdown('**', '**', '加粗文本')" :disabled="loading" title="加粗"><strong>B</strong></button>
            <button type="button" @click="insertMarkdown('*', '*', '斜体文本')" :disabled="loading" title="斜体"><em>I</em></button>
            <button type="button" @click="insertMarkdown('~~', '~~', '删除线')" :disabled="loading" title="删除线"><del>S</del></button>
            <span class="toolbar-divider"></span>
            <button type="button" @click="insertMarkdown('# ', '', '一级标题')" :disabled="loading">H1</button>
            <button type="button" @click="insertMarkdown('## ', '', '二级标题')" :disabled="loading">H2</button>
            <button type="button" @click="insertMarkdown('### ', '', '三级标题')" :disabled="loading">H3</button>
            <span class="toolbar-divider"></span>
            <button type="button" @click="insertMarkdown('- ', '', '无序列表')" :disabled="loading">&bull;</button>
            <button type="button" @click="insertMarkdown('1. ', '', '有序列表')" :disabled="loading">1.</button>
            <span class="toolbar-divider"></span>
            <button type="button" @click="insertMarkdown('```\n', '\n```', '代码块')" :disabled="loading" title="代码块">&lt;/&gt;</button>
            <button type="button" @click="insertMarkdown('`', '`', '行内代码')" :disabled="loading" title="行内代码">`</button>
            <button type="button" @click="insertMarkdown('[', '](url)', '链接')" :disabled="loading" title="链接">Link</button>
          </div>

          <!-- Editor / Preview -->
          <textarea
            v-if="!showPreview"
            id="content"
            v-model="content"
            rows="15"
            required
            :disabled="loading"
            class="input-field editor-textarea"
            placeholder="输入文章内容，支持 Markdown 格式..."
          ></textarea>
          <div
            v-else
            class="preview-pane markdown-body"
            v-html="renderedContent"
          ></div>
        </div>

        <div class="form-card">
          <div class="form-group">
            <label>图片</label>
            <div v-if="images.length > 0" class="image-grid">
              <div v-for="(image, index) in images" :key="index" class="image-thumb">
                <img :src="image" :alt="`图片 ${index + 1}`" />
                <button type="button" @click="removeImage(index)" :disabled="loading" class="image-remove">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>
            </div>
            <input ref="fileInput" type="file" accept="image/*" style="display:none;" @change="handleFileSelect" />
            <button type="button" @click="addImage" class="btn btn-ghost upload-btn" :disabled="loading">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              添加图片
            </button>
          </div>
        </div>

        <div v-if="error" class="message-error">{{ error }}</div>
        <div v-if="success" class="message-success">{{ success }}</div>

        <button type="submit" class="btn btn-primary publish-submit" :disabled="loading">
          <span v-if="loading" class="spinner-ring" style="width:16px;height:16px;border-width:2px;"></span>
          <span v-else>{{ loading ? '发布中...' : '发布文章' }}</span>
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.publish-page {
  max-width: 860px;
  margin: 0 auto;
}

.publish-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.auto-save-bar {
  text-align: right;
  margin-bottom: 0;
}

.save-status {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: 0.8rem;
  font-weight: 500;
  padding: 6px 12px;
  border-radius: var(--radius-full);
}

.save-status.saving {
  color: var(--color-accent);
  background: rgba(59, 130, 246, 0.06);
}

.save-status.saved {
  color: var(--color-success);
  background: rgba(16, 185, 129, 0.06);
}

.page-heading {
  margin-bottom: 0;
}

.page-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--color-primary);
  letter-spacing: -0.03em;
  margin-bottom: var(--spacing-xs);
}

.page-subtitle {
  font-size: 0.9rem;
  color: var(--color-secondary);
  font-weight: 400;
}

.publish-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.form-card {
  background: var(--color-card-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  padding: var(--spacing-xl);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.form-group + .form-group {
  margin-top: var(--spacing-lg);
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-primary);
  letter-spacing: -0.01em;
}

.title-input {
  font-size: 1.1rem;
  font-weight: 600;
  padding: 12px 16px;
}

.select-wrapper {
  position: relative;
}

.select-wrapper::after {
  content: '';
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 5px solid var(--color-secondary);
  pointer-events: none;
}

.select-wrapper select {
  width: 100%;
  padding: 10px 36px 10px 14px;
  border: 1px solid var(--color-input-border);
  border-radius: var(--radius-input);
  background: var(--color-input-bg);
  color: var(--color-primary);
  font-family: var(--font-stack);
  font-size: 0.9rem;
  appearance: none;
  -webkit-appearance: none;
  cursor: pointer;
  transition: all var(--transition-fast);
  outline: none;
}

.select-wrapper select:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* Editor Card */
.editor-card {
  padding: 0;
  overflow: hidden;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-glass-border);
  background: var(--color-input-bg);
}

.editor-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-primary);
}

.editor-actions {
  display: flex;
  gap: var(--spacing-sm);
}

/* MD Toolbar */
.md-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  padding: var(--spacing-sm) var(--spacing-md);
  border-bottom: 1px solid var(--color-glass-border);
  background: var(--color-input-bg);
}

.md-toolbar button {
  padding: 5px 10px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  color: var(--color-secondary);
  font-family: var(--font-stack);
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  line-height: 1;
}

.md-toolbar button:hover:not(:disabled) {
  background: var(--color-hover);
  color: var(--color-primary);
  border-color: var(--color-glass-border);
}

.md-toolbar button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.md-toolbar button strong,
.md-toolbar button em,
.md-toolbar button del {
  font-style: normal;
}

.toolbar-divider {
  width: 1px;
  height: 18px;
  background: var(--color-glass-border);
  margin: 0 4px;
}

/* Textarea */
.editor-textarea {
  min-height: 350px;
  border: none;
  border-radius: 0;
  resize: vertical;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  line-height: 1.7;
  padding: var(--spacing-lg);
}

.editor-textarea:focus {
  box-shadow: none;
  border: none;
}

/* Preview */
.preview-pane {
  min-height: 350px;
  padding: var(--spacing-xl);
  overflow-y: auto;
}

/* Images */
.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.image-thumb {
  position: relative;
  aspect-ratio: 1;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--color-glass-border);
}

.image-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(225, 29, 72, 0.85);
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.image-thumb:hover .image-remove {
  opacity: 1;
}

.upload-btn {
  width: 100%;
  justify-content: center;
  padding: 12px;
  border-style: dashed;
}

/* Submit */
.publish-submit {
  width: 100%;
  padding: 14px 20px;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
}

@media (max-width: 768px) {
  .form-card {
    padding: var(--spacing-lg);
  }

  .editor-textarea {
    min-height: 250px;
  }
}
</style>