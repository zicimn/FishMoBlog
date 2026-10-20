<script setup lang="ts">
import { ref } from 'vue'
import request from '@/api/request'

const activeTool = ref('compression')
const windowObj = window

interface Tool {
  id: string
  name: string
  icon: string
  description: string
}

const tools = ref<Tool[]>([
  { id: 'compression', name: '图片压缩', icon: '', description: '压缩图片体积' },
  { id: 'diviation', name: '今日运势', icon: '', description: '测试今日运势' },
  { id: 'watermark', name: '', icon: '', description: '' },
  { id: 'format', name: '', icon: '', description: '' },
  { id: 'resize', name: '', icon: '', description: '' },
  { id: 'crop', name: '', icon: '', description: '' },
  { id: 'tool7', name: '', icon: '', description: '' },
  { id: 'tool8', name: '', icon: '', description: '' }
])

const compressionImages = ref<File[]>([])
const compressionQuality = ref(80)
const compressionStyle = ref('webp')
const compressionResults = ref<string[]>([])
const compressionLoading = ref(false)
const compressionError = ref('')

const compressedImages = ref<{ name: string; url: string; size: number }[]>([])

// 命运测试相关
const diviationLoading = ref(false)
const diviationError = ref('')
const diviationData = ref<{ user_id: number; fate: string; url: string } | null>(null)

const handleToolClick = (toolId: string) => {
  // 查找工具对象
  const tool = tools.value.find(t => t.id === toolId)
  if (!tool || !tool.name) {
    return // 空白卡片不做任何操作
  }
  
  activeTool.value = toolId
  if (toolId === 'diviation') {
    handleDiviation()
  } else if (toolId !== 'compression') {
    alert('该功能正在开发中，敬请期待！')
  }
}

const handleImageUpload = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files) {
    const files = Array.from(target.files)
    compressionImages.value = [...compressionImages.value, ...files]
    compressionError.value = ''
  }
}

const removeImage = (index: number) => {
  compressionImages.value.splice(index, 1)
}

const handleCompression = async () => {
  if (compressionImages.value.length === 0) {
    compressionError.value = '请至少上传一张图片'
    return
  }

  compressionLoading.value = true
  compressionError.value = ''
  compressedImages.value = []

  try {
    const base64Images = await Promise.all(
      compressionImages.value.map(file => {
        return new Promise<string>((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => resolve(reader.result as string)
          reader.onerror = reject
          reader.readAsDataURL(file)
        })
      })
    )

    const response = await request.post('/tools/compression', {
      images: base64Images,
      quality: compressionQuality.value,
      style: compressionStyle.value
    })

    compressionResults.value = response.data.images

    compressionResults.value.forEach((base64, index) => {
      const parts = base64.split(',')
      if (parts.length < 2) return
      
      const byteString = atob(parts[1] || '')
      const mimePart = parts[0]?.split(':')[1]
      if (!mimePart) return
      const mimeString = mimePart.split(';')[0]
      
      const ab = new ArrayBuffer(byteString.length)
      const ia = new Uint8Array(ab)
      for (let i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i)
      }
      const blob = new Blob([ab], { type: mimeString })
      const url = windowObj.URL.createObjectURL(blob)

      const originalImage = compressionImages.value[index]
      if (!originalImage) return

      compressedImages.value.push({
        name: `${originalImage.name.split('.')[0]}.${compressionStyle.value}`,
        url: url,
        size: blob.size
      })
    })
  } catch (error: unknown) {
    let errorMessage = '压缩失败，请稍后重试'
    if (typeof error === 'object' && error !== null) {
      // 安全地访问错误对象的属性
      if ('response' in error && typeof error.response === 'object' && error.response !== null) {
        const response = error.response
        if ('data' in response && typeof response.data === 'object' && response.data !== null) {
          const data = response.data
          if ('detail' in data && typeof data.detail === 'string') {
            errorMessage = data.detail
          }
        }
      } else if ('message' in error && typeof error.message === 'string') {
        errorMessage = error.message
      }
    }
    compressionError.value = errorMessage
    console.error('Compression failed:', error)
  } finally {
    compressionLoading.value = false
  }
}

const downloadImage = (image: { name: string; url: string }) => {
  const link = document.createElement('a')
  link.href = image.url
  link.download = image.name
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const downloadAllImages = () => {
  compressedImages.value.forEach((image, index) => {
    setTimeout(() => {
      downloadImage(image)
    }, index * 200)
  })
}

const clearCompression = () => {
  compressionImages.value = []
  compressionResults.value = []
  compressedImages.value = []
  compressionError.value = ''
}

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

const handleDiviation = async () => {
  diviationLoading.value = true
  diviationError.value = ''
  diviationData.value = null
  
  try {
    const response = await request.get('/tools/diviation')
    diviationData.value = response.data
  } catch (error: unknown) {
    let errorMessage = '获取命运测试失败，请稍后重试'
    if (typeof error === 'object' && error !== null) {
      if ('response' in error && typeof error.response === 'object' && error.response !== null) {
        const response = error.response
        if ('data' in response && typeof response.data === 'object' && response.data !== null) {
          const data = response.data
          if ('detail' in data && typeof data.detail === 'string') {
            errorMessage = data.detail
          }
        }
      } else if ('message' in error && typeof error.message === 'string') {
        errorMessage = error.message
      }
    }
    diviationError.value = errorMessage
    console.error('Diviation failed:', error)
  } finally {
    diviationLoading.value = false
  }
}
</script>

<template>
  <div class="tools-page">
    <div class="page-heading">
      <h1 class="page-title">工具箱</h1>
      <p class="page-subtitle">提供多种工具，让您的工作更加便捷</p>
    </div>

    <div class="tools-grid">
      <div
        v-for="tool in tools"
        :key="tool.id"
        class="tool-card"
        :class="{ active: activeTool === tool.id, empty: !tool.name }"
        @click="handleToolClick(tool.id)"
      >
        <div class="tool-icon" v-if="tool.name">
          <svg v-if="tool.id === 'compression'" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          <svg v-else-if="tool.id === 'diviation'" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        </div>
        <div class="tool-name" v-if="tool.name">{{ tool.name }}</div>
        <div class="tool-description" v-if="tool.description">{{ tool.description }}</div>
      </div>
    </div>

    <!-- Compression Tool -->
    <transition name="fade" mode="out-in">
      <div v-if="activeTool === 'compression'" key="compression" class="tool-panel">
        <div class="panel-header">
          <h2 class="panel-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            图片压缩
          </h2>
        </div>

        <div class="upload-zone" @dragover.prevent>
          <input type="file" id="image-upload" accept="image/*" multiple @change="handleImageUpload" class="file-input" />
          <label for="image-upload" class="upload-label">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="upload-icon"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <span class="upload-text">点击选择图片</span>
            <span class="upload-hint">支持多选，最多10张图片</span>
          </label>
        </div>

        <div v-if="compressionImages.length > 0" class="selected-section">
          <div class="section-line">
            <span class="line-label">已选择 {{ compressionImages.length }} 张</span>
            <button @click="clearCompression" class="btn btn-ghost" style="font-size:0.8rem;padding:4px 12px;">清空</button>
          </div>
          <div class="thumb-grid">
            <div v-for="(image, index) in compressionImages" :key="index" class="thumb-item">
              <img :src="windowObj.URL.createObjectURL(image)" alt="" class="thumb-img" />
              <div class="thumb-meta">
                <span class="thumb-name">{{ image.name }}</span>
                <span class="thumb-size">{{ formatFileSize(image.size) }}</span>
              </div>
              <button @click="removeImage(index)" class="thumb-remove">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
          </div>
        </div>

        <div class="options-row">
          <div class="option-card">
            <label class="option-label">压缩质量</label>
            <div class="slider-group">
              <input type="range" min="10" max="100" v-model="compressionQuality" class="range-slider" />
              <span class="range-value">{{ compressionQuality }}%</span>
            </div>
          </div>
          <div class="option-card">
            <label class="option-label">输出格式</label>
            <div class="format-group">
              <button class="format-chip" :class="{ active: compressionStyle === 'webp' }" @click="compressionStyle = 'webp'">WebP</button>
              <button class="format-chip" :class="{ active: compressionStyle === 'jpg' }" @click="compressionStyle = 'jpg'">JPEG</button>
              <button class="format-chip" :class="{ active: compressionStyle === 'png' }" @click="compressionStyle = 'png'">PNG</button>
            </div>
          </div>
        </div>

        <div v-if="compressionError" class="message-error">{{ compressionError }}</div>

        <button @click="handleCompression" :disabled="compressionImages.length === 0 || compressionLoading" class="btn btn-primary action-btn">
          <span v-if="compressionLoading" class="spinner-ring" style="width:16px;height:16px;border-width:2px;"></span>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          {{ compressionLoading ? '压缩中...' : '开始压缩' }}
        </button>

        <div v-if="compressedImages.length > 0" class="results-section">
          <div class="section-line">
            <span class="line-label">压缩结果 ({{ compressedImages.length }} 张)</span>
            <button @click="downloadAllImages" class="btn btn-ghost" style="font-size:0.8rem;padding:4px 12px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              下载全部
            </button>
          </div>
          <div class="result-grid">
            <div v-for="(image, index) in compressedImages" :key="index" class="result-card">
              <img :src="image.url" alt="" class="result-img" />
              <div class="result-meta">
                <span class="result-name">{{ image.name }}</span>
                <span class="result-size">{{ formatFileSize(image.size) }}</span>
              </div>
              <button @click="downloadImage(image)" class="btn btn-primary" style="font-size:0.8rem;padding:6px 16px;width:100%;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                下载
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Divination Tool -->
      <div v-else-if="activeTool === 'diviation'" key="diviation" class="tool-panel">
        <div class="panel-header">
          <h2 class="panel-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            今日运势
          </h2>
        </div>

        <div v-if="diviationLoading" class="loading-spinner" style="padding:var(--spacing-3xl);">
          <div class="spinner-ring"></div>
          <span class="loading-text">正在获取今日运势...</span>
        </div>

        <div v-else-if="diviationError" class="message-error">{{ diviationError }}</div>

        <div v-else-if="diviationData" class="divination-result">
          <div class="divination-layout">
            <div class="divination-image">
              <img :src="diviationData.url" alt="今日运势" class="fate-image" />
            </div>
            <div class="divination-body">
              <h3 class="fate-heading">今日运势</h3>
              <div class="fate-content">{{ diviationData.fate }}</div>
              <div class="fate-user">用户 ID: {{ diviationData.user_id }}</div>
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          <div class="empty-state-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          </div>
          <p class="empty-state-text">点击上方的「今日运势」按钮开始测试</p>
        </div>
      </div>

      <!-- Coming Soon -->
      <div v-else key="coming-soon" class="tool-panel coming-soon-panel">
        <div class="coming-soon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          <h3>功能开发中</h3>
          <p>敬请期待</p>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.tools-page {
  max-width: 960px;
  margin: 0 auto;
}

.page-heading {
  margin-bottom: var(--spacing-xl);
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

/* Grid */
.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
}

.tool-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-lg) var(--spacing-md);
  background: var(--color-card-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: all var(--transition-normal);
  text-align: center;
  min-height: 110px;
}

.tool-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-elevated);
  border-color: var(--color-accent);
}

.tool-card.active {
  border-color: var(--color-accent);
  background: rgba(59, 130, 246, 0.06);
}

.tool-card.empty {
  opacity: 0.35;
  cursor: default;
  border-style: dashed;
}

.tool-card.empty:hover {
  transform: none;
  box-shadow: var(--shadow-card);
  border-color: var(--color-card-border);
}

.tool-icon {
  color: var(--color-secondary);
  transition: color var(--transition-fast);
}

.tool-card:not(.empty):hover .tool-icon,
.tool-card.active .tool-icon {
  color: var(--color-accent);
}

.tool-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-primary);
}

.tool-description {
  font-size: 0.75rem;
  color: var(--color-secondary);
}

/* Tool Panel */
.tool-panel {
  background: var(--color-card-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  padding: var(--spacing-xl);
}

.panel-header {
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--color-glass-border);
}

.panel-title {
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--color-primary);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

/* Upload Zone */
.file-input {
  display: none;
}

.upload-zone {
  margin-bottom: var(--spacing-lg);
}

.upload-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  padding: var(--spacing-2xl);
  border: 2px dashed var(--color-glass-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.upload-label:hover {
  border-color: var(--color-accent);
  background: rgba(59, 130, 246, 0.03);
}

.upload-icon {
  color: var(--color-secondary);
  opacity: 0.4;
}

.upload-text {
  font-size: 1rem;
  font-weight: 500;
  color: var(--color-primary);
}

.upload-hint {
  font-size: 0.8rem;
  color: var(--color-secondary);
}

/* Selected Images */
.selected-section {
  margin-bottom: var(--spacing-lg);
}

.section-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.line-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-primary);
}

.thumb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--spacing-sm);
}

.thumb-item {
  position: relative;
  padding: var(--spacing-sm);
  background: var(--color-input-bg);
  border: 1px solid var(--color-glass-border);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.thumb-img {
  width: 100%;
  height: 80px;
  object-fit: cover;
  border-radius: 4px;
}

.thumb-meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
}

.thumb-name {
  font-size: 0.75rem;
  color: var(--color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.thumb-size {
  font-size: 0.7rem;
  color: var(--color-secondary);
}

.thumb-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(225, 29, 72, 0.8);
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.thumb-item:hover .thumb-remove {
  opacity: 1;
}

/* Options */
.options-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.option-card {
  padding: var(--spacing-lg);
  background: var(--color-input-bg);
  border: 1px solid var(--color-glass-border);
  border-radius: var(--radius-sm);
}

.option-label {
  display: block;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: var(--spacing-md);
  letter-spacing: -0.01em;
}

.slider-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.range-slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  border-radius: 3px;
  background: var(--color-glass-border);
  outline: none;
  cursor: pointer;
}

.range-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-accent);
  cursor: pointer;
}

.range-value {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--color-accent);
  min-width: 45px;
  text-align: right;
}

.format-group {
  display: flex;
  gap: var(--spacing-xs);
}

.format-chip {
  flex: 1;
  padding: 8px 12px;
  background: transparent;
  border: 1px solid var(--color-glass-border);
  border-radius: var(--radius-sm);
  color: var(--color-secondary);
  font-family: var(--font-stack);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.format-chip:hover {
  border-color: var(--color-accent);
  color: var(--color-primary);
}

.format-chip.active {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: white;
}

/* Action */
.action-btn {
  width: 100%;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  font-size: 0.95rem;
}

/* Results */
.results-section {
  margin-top: var(--spacing-xl);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-glass-border);
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--spacing-md);
}

.result-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--color-input-bg);
  border: 1px solid var(--color-glass-border);
  border-radius: var(--radius-sm);
}

.result-img {
  width: 100%;
  height: 120px;
  object-fit: contain;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.02);
}

.result-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 var(--spacing-xs);
}

.result-name {
  font-size: 0.8rem;
  color: var(--color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-size {
  font-size: 0.75rem;
  color: var(--color-success);
  font-weight: 600;
}

/* Divination */
.divination-result {
  padding: var(--spacing-md) 0;
}

.divination-layout {
  display: flex;
  gap: var(--spacing-xl);
  align-items: flex-start;
}

.divination-image {
  flex: 1;
  max-width: 50%;
}

.fate-image {
  width: 100%;
  height: auto;
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-card);
}

.divination-body {
  flex: 1;
  padding: var(--spacing-lg);
  background: var(--color-input-bg);
  border: 1px solid var(--color-glass-border);
  border-radius: var(--radius-sm);
}

.fate-heading {
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--color-primary);
  text-align: center;
  margin-bottom: var(--spacing-md);
}

.fate-content {
  font-size: 1rem;
  line-height: 1.7;
  color: var(--color-primary);
  margin-bottom: var(--spacing-lg);
  text-align: center;
}

.fate-user {
  font-size: 0.8rem;
  color: var(--color-secondary);
  text-align: center;
}

/* Coming Soon */
.coming-soon-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 250px;
}

.coming-soon {
  text-align: center;
  color: var(--color-secondary);
}

.coming-soon svg {
  opacity: 0.3;
  margin-bottom: var(--spacing-lg);
}

.coming-soon h3 {
  font-size: 1.3rem;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: var(--spacing-xs);
}

.coming-soon p {
  font-size: 0.9rem;
  color: var(--color-secondary);
}

/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s var(--transition-base);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .tools-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-sm);
  }

  .options-row {
    grid-template-columns: 1fr;
  }

  .divination-layout {
    flex-direction: column;
  }

  .divination-image {
    max-width: 100%;
  }
}
</style>