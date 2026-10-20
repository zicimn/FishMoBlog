<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { articleApi, type ArticleEditRequest, type ArticleDetailResponse } from '@/api/article'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const articleId = ref(Number(route.params.id))
const articleAuthorId = ref<number | undefined>(undefined)

const title = ref('')
const category = ref('')
const content = ref('')
const images = ref<string[]>([])
const imagesString = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

const loading = ref(true)
const error = ref('')
const success = ref('')
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

const categories = ['all', 'code', 'health', 'other', 'test', 'study']

const fetchArticle = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await articleApi.visit(articleId.value)
    const data = response.data as ArticleDetailResponse & { category?: string }
    title.value = data.title
    content.value = data.content
    category.value = data.category || ''
    images.value = data.images || []
    imagesString.value = images.value.join(', ')
    articleAuthorId.value = data.author_id
    
    // 检查权限
    console.log('User is logged in:', userStore.isLoggedIn)
    console.log('User ID:', userStore.id)
    console.log('Article author ID:', articleAuthorId.value)
    console.log('Match:', articleAuthorId.value === userStore.id)
    
    if (!userStore.isLoggedIn) {
      error.value = 'You are not logged in'
      setTimeout(() => {
        router.push(`/article/${articleId.value}`)
      }, 2000)
    } else if (!articleAuthorId.value) {
      error.value = '加载不出来'
      setTimeout(() => {
        router.push(`/article/${articleId.value}`)
      }, 2000)
    } else if (articleAuthorId.value !== userStore.id) {
      error.value = 'You do not have permission to edit this article'
      setTimeout(() => {
        router.push(`/article/${articleId.value}`)
      }, 2000)
    }
  } catch (err: unknown) {
    error.value = '加载不出来'
    console.error(err)
  } finally {
    loading.value = false
  }
}

const handleSubmit = async () => {
  if (!title.value || !content.value || !category.value) {
    error.value = 'Please fill in all required fields'
    return
  }

  loading.value = true
  error.value = ''
  success.value = ''
  
  try {
    const data: ArticleEditRequest = {
      title: title.value,
      category: category.value,
      content: content.value,
      images: images.value || []
    }
    console.log('Sending edit request with data:', data)
    console.log('Article ID:', articleId.value)
    await articleApi.edit(articleId.value, data)
    success.value = '文章更新成功'
    // 编辑成功后跳转到文章详情页
    setTimeout(() => {
      router.push(`/article/${articleId.value}`)
    }, 2000)
  } catch (err: unknown) {
    console.error('更新文章失败:', err)
    if (err instanceof Error) {
      error.value = `更新文章失败: ${err.message}`
    } else {
      error.value = '更新文章失败'
    }
  } finally {
    loading.value = false
  }
}

const handleBack = () => {
  const from = route.query.from || route.params.from
  if (from) {
    router.push(String(from))
  } else {
    router.push('/control')
  }
}

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
        imagesString.value = images.value.join(', ')
        error.value = '' // 清除错误信息
      }
      reader.readAsDataURL(file)
    }
  }
}

const removeImage = (index: number) => {
  images.value.splice(index, 1)
  imagesString.value = images.value.join(', ')
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

onMounted(() => {
  fetchArticle()
})
</script>

<template>
  <div class="edit-article">
    <div class="publish-container">
      <div class="page-heading">
        <h1 class="page-title">编辑文章</h1>
        <p class="page-subtitle">修改您的文章内容</p>
      </div>

      <div v-if="loading" class="loading-spinner">
        <div class="spinner-ring"></div>
        <span class="loading-text">加载中...</span>
      </div>

      <div v-else class="edit-form">
        <div class="form-card">
          <div class="form-group">
            <label for="title">标题</label>
            <input type="text" id="title" v-model="title" required :disabled="loading" class="input-field title-input" placeholder="输入文章标题" />
          </div>
          <div class="form-group">
            <label for="category">分类</label>
            <div class="select-wrapper">
              <select id="category" v-model="category" required :disabled="loading">
                <option value="">选择分类</option>
                <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
              </select>
            </div>
          </div>
        </div>

        <div class="form-card editor-card">
          <div class="editor-header">
            <label class="editor-label">内容 (支持 Markdown)</label>
            <div class="editor-actions">
              <button type="button" @click="showPreview = !showPreview" class="btn btn-ghost" :disabled="loading" style="font-size:0.8rem;padding:6px 14px;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                {{ showPreview ? '编辑' : '预览' }}
              </button>
            </div>
          </div>

          <div class="md-toolbar">
            <button type="button" @click="insertMarkdown('**', '**', '加粗文本')" :disabled="loading"><strong>B</strong></button>
            <button type="button" @click="insertMarkdown('*', '*', '斜体文本')" :disabled="loading"><em>I</em></button>
            <button type="button" @click="insertMarkdown('~~', '~~', '删除线')" :disabled="loading"><del>S</del></button>
            <span class="toolbar-divider"></span>
            <button type="button" @click="insertMarkdown('# ', '', '一级标题')" :disabled="loading">H1</button>
            <button type="button" @click="insertMarkdown('## ', '', '二级标题')" :disabled="loading">H2</button>
            <button type="button" @click="insertMarkdown('### ', '', '三级标题')" :disabled="loading">H3</button>
            <span class="toolbar-divider"></span>
            <button type="button" @click="insertMarkdown('- ', '', '无序列表')" :disabled="loading">&bull;</button>
            <button type="button" @click="insertMarkdown('1. ', '', '有序列表')" :disabled="loading">1.</button>
            <span class="toolbar-divider"></span>
            <button type="button" @click="insertMarkdown('```\n', '\n```', '代码块')" :disabled="loading">&lt;/&gt;</button>
            <button type="button" @click="insertMarkdown('`', '`', '行内代码')" :disabled="loading">`</button>
            <button type="button" @click="insertMarkdown('[', '](url)', '链接')" :disabled="loading">Link</button>
          </div>

          <textarea v-if="!showPreview" id="content" v-model="content" rows="12" required :disabled="loading" class="input-field editor-textarea" placeholder="输入文章内容，支持 Markdown 格式..."></textarea>
          <div v-else class="preview-pane markdown-body" v-html="renderedContent"></div>
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

        <div class="form-actions">
          <button type="button" class="btn btn-ghost" :disabled="loading" @click="handleBack">
            返回
          </button>
          <button type="button" class="btn btn-primary" :disabled="loading" @click="handleSubmit" style="flex:1;">
            <span v-if="loading" class="spinner-ring" style="width:16px;height:16px;border-width:2px;"></span>
            <span v-else>{{ loading ? '更新中...' : '更新文章' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.edit-article {
  max-width: 860px;
  margin: 0 auto;
}

.publish-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
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

.edit-form {
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

.toolbar-divider {
  width: 1px;
  height: 18px;
  background: var(--color-glass-border);
  margin: 0 4px;
}

.editor-textarea {
  min-height: 300px;
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

.preview-pane {
  min-height: 300px;
  padding: var(--spacing-xl);
  overflow-y: auto;
}

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

.form-actions {
  display: flex;
  gap: var(--spacing-md);
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