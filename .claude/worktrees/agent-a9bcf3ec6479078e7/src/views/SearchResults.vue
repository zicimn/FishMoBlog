<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '@/api/request'

interface SearchResult {
  id: number
  title: string
  author_id: number
  category: string
  views: number
  likes: number
  created_at: string
}

const route = useRoute()
const router = useRouter()
const searchResults = ref<SearchResult[]>([])
const loading = ref(false)
const error = ref('')
const searchWord = ref('')

// 分页相关状态
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

onMounted(async () => {
  const word = route.params.word as string
  searchWord.value = word
  currentPage.value = 1 // 重置页码
  await fetchSearchResults(word, currentPage.value, pageSize.value)
})

// 监听路由参数变化，当搜索关键词改变时重新搜索
watch(() => route.params.word, async (newWord) => {
  if (newWord) {
    const word = newWord as string
    searchWord.value = word
    currentPage.value = 1 // 重置页码
    await fetchSearchResults(word, currentPage.value, pageSize.value)
  }
}, { immediate: false })

const fetchSearchResults = async (word: string, page: number = 1, size: number = 10) => {
  loading.value = true
  error.value = ''
  try {
    console.log('开始搜索:', word, 'page:', page, 'size:', size)
    console.log('请求URL:', `/search/${encodeURIComponent(word)}?page=${page}&size=${size}`)
    const response = await request.get(`/search/${encodeURIComponent(word)}`, {
      params: {
        page,
        size
      }
    })
    console.log('搜索成功:', response.data)
    searchResults.value = response.data.result
    // 假设API返回total字段
    if ('total' in response.data) {
      total.value = response.data.total
    }
  } catch (err) {
    error.value = '搜索失败，请稍后重试'
    console.error('搜索失败:', err)
    if (err instanceof Error) {
      console.error('错误详情:', err.message)
    }
    // 安全地处理错误响应
    if (typeof err === 'object' && err !== null && 'response' in err) {
      console.error('错误响应:', err.response)
    }
  } finally {
    loading.value = false
    console.log('搜索结束')
  }
}

const goToArticle = (id: number) => {
  router.push(`/article/${id}`)
}

const changePage = async (page: number) => {
  if (page < 1) return
  currentPage.value = page
  const word = searchWord.value
  await fetchSearchResults(word, currentPage.value, pageSize.value)
}
</script>

<template>
  <div class="search-results-page">
    <div class="page-heading">
      <h1 class="page-title">搜索结果</h1>
      <p class="page-subtitle">{{ searchWord }}</p>
    </div>

    <div v-if="loading" class="loading-spinner">
      <div class="spinner-ring"></div>
      <span class="loading-text">正在搜索...</span>
    </div>

    <div v-else-if="error" class="message-error">{{ error }}</div>

    <div v-else-if="searchResults.length === 0" class="empty-state">
      <div class="empty-state-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      </div>
      <p class="empty-state-text">未找到相关文章</p>
    </div>

    <div v-else class="results-list">
      <div
        v-for="article in searchResults"
        :key="article.id"
        class="article-card"
        @click="goToArticle(article.id)"
      >
        <h3 class="article-title">{{ article.title }}</h3>
        <div class="article-meta">
          <span class="meta-item">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            {{ article.author_id }}
          </span>
          <span class="meta-tag">{{ article.category }}</span>
          <span class="meta-item">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            {{ new Date(article.created_at).toLocaleDateString() }}
          </span>
        </div>
        <div class="article-stats">
          <span class="stat">{{ article.views }} views</span>
          <span class="stat">{{ article.likes }} likes</span>
        </div>
      </div>

      <div class="pagination" v-if="total > pageSize">
        <button
          @click="changePage(currentPage - 1)"
          :disabled="currentPage === 1"
          class="pagination-btn"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          上一页
        </button>
        <span class="pagination-info">
          第 {{ currentPage }} / {{ Math.ceil(total / pageSize) }} 页
        </span>
        <button
          @click="changePage(currentPage + 1)"
          :disabled="currentPage >= Math.ceil(total / pageSize)"
          class="pagination-btn"
        >
          下一页
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.search-results-page {
  max-width: 860px;
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

.results-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.article-card {
  padding: var(--spacing-lg);
  background: var(--color-card-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  transition: all var(--transition-normal);
  cursor: pointer;
}

.article-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-elevated);
  border-color: rgba(59, 130, 246, 0.2);
}

.article-title {
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: var(--spacing-sm);
  letter-spacing: -0.02em;
  line-height: 1.4;
}

.article-meta {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
  margin-bottom: var(--spacing-sm);
  flex-wrap: wrap;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.8rem;
  color: var(--color-secondary);
}

.meta-tag {
  display: inline-block;
  padding: 2px 10px;
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--color-accent);
  background: rgba(59, 130, 246, 0.06);
  border-radius: var(--radius-full);
  text-transform: lowercase;
}

.article-stats {
  display: flex;
  gap: var(--spacing-lg);
}

.stat {
  font-size: 0.8rem;
  color: var(--color-secondary);
  font-weight: 500;
}

/* Pagination inherits from global styles */
</style>