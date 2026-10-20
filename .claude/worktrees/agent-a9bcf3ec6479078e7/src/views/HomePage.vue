<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { articleApi } from '@/api/article'
import type { ArticleItem } from '@/api/article'

const articles = ref<ArticleItem[]>([])
const loading = ref(true)
const error = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const selectedCategory = ref<string>('')
const selectedSort = ref<string>('created_at')
const selectedOrder = ref<string>('desc')

const categories = ['all', 'code', 'health', 'other', 'test', 'study']
const sortOptions = [
  { value: 'created_at', label: '发布时间' },
  { value: 'views', label: '浏览量' },
  { value: 'likes', label: '点赞数' }
]
const orderOptions = [
  { value: 'desc', label: '降序' },
  { value: 'asc', label: '升序' }
]

const fetchArticles = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await articleApi.list(
      currentPage.value, 
      pageSize.value, 
      selectedCategory.value || undefined,
      selectedSort.value,
      selectedOrder.value
    )
    articles.value = response.data?.items || []
    total.value = response.data?.total || 0
  } catch (err) {
    error.value = '加载不出来'
    articles.value = []
    total.value = 0
    console.error(err)
  } finally {
    loading.value = false
  }
}

const handleCategoryChange = (category: string) => {
  selectedCategory.value = category
  currentPage.value = 1
  fetchArticles()
}

const handleSortChange = () => {
  currentPage.value = 1
  fetchArticles()
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchArticles()
}

onMounted(() => {
  fetchArticles()
})
</script>

<template>
  <div class="home-page">
    <div class="page-heading">
      <h1 class="page-title">文章列表</h1>
      <p class="page-subtitle">浏览社区最新内容</p>
    </div>

    <div class="filter-bar">
      <div class="categories">
        <button
          v-for="category in categories"
          :key="category"
          :class="{ active: (category === 'all' && selectedCategory === '') || selectedCategory === category }"
          @click="handleCategoryChange(category === 'all' ? '' : category)"
        >
          {{ category }}
        </button>
      </div>

      <div class="sort-group">
        <div class="sort-select-wrapper">
          <select v-model="selectedSort" @change="handleSortChange">
            <option v-for="option in sortOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
        <div class="sort-select-wrapper">
          <select v-model="selectedOrder" @change="handleSortChange">
            <option v-for="option in orderOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-spinner">
      <div class="spinner-ring"></div>
      <span class="loading-text">加载中...</span>
    </div>

    <div v-else-if="error" class="message-error">{{ error }}</div>

    <div v-else>
      <div class="article-grid">
        <div v-for="article in (articles || [])" :key="article.id" class="article-card">
          <router-link :to="`/article/${article.id}`" class="article-title">
            {{ article.title }}
          </router-link>
          <div class="article-meta">
            <span class="meta-item">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              {{ new Date(article.create_at).toLocaleDateString() }}
            </span>
            <span class="meta-tag">{{ article.category }}</span>
          </div>
          <div class="article-stats">
            <span class="stat">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              {{ article.views }}
            </span>
            <span class="stat">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>
              {{ article.likes }}
            </span>
          </div>
          <div class="card-fade"></div>
        </div>

        <div v-if="(articles || []).length === 0" class="empty-state">
          <div class="empty-state-icon">---</div>
          <p class="empty-state-text">暂无文章</p>
        </div>
      </div>

      <div class="pagination" v-if="total > 0">
        <button
          @click="handlePageChange(currentPage - 1)"
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
          @click="handlePageChange(currentPage + 1)"
          :disabled="(currentPage * pageSize) >= total"
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
.home-page {
  max-width: 900px;
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

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-md);
  background: var(--color-card-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}

.categories {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.categories button {
  padding: 6px 14px;
  border: 1px solid var(--color-glass-border);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--color-secondary);
  font-family: var(--font-stack);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.categories button:hover {
  background: var(--color-hover);
  color: var(--color-primary);
  border-color: var(--color-accent);
}

.categories button.active {
  background: var(--color-accent);
  color: white;
  border-color: var(--color-accent);
}

.sort-group {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
}

.sort-select-wrapper {
  position: relative;
}

.sort-select-wrapper::after {
  content: '';
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 4px solid var(--color-secondary);
  pointer-events: none;
}

.sort-select-wrapper select {
  padding: 6px 28px 6px 12px;
  border: 1px solid var(--color-glass-border);
  border-radius: var(--radius-button);
  background: var(--color-input-bg);
  color: var(--color-primary);
  font-family: var(--font-stack);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  transition: all var(--transition-fast);
  outline: none;
}

.sort-select-wrapper select:hover {
  border-color: var(--color-accent);
}

.sort-select-wrapper select:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.article-grid {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.article-card {
  position: relative;
  overflow: hidden;
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
  text-decoration: none;
  display: block;
  margin-bottom: var(--spacing-sm);
  line-height: 1.4;
  letter-spacing: -0.02em;
  transition: color var(--transition-fast);
}

.article-title:hover {
  color: var(--color-accent);
}

.article-meta {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
  margin-bottom: var(--spacing-sm);
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
  letter-spacing: 0.02em;
  text-transform: lowercase;
}

.article-stats {
  display: flex;
  gap: var(--spacing-lg);
}

.stat {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.8rem;
  color: var(--color-secondary);
  font-weight: 500;
}

.card-fade {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-accent), transparent);
  opacity: 0;
  transition: opacity var(--transition-normal);
}

.article-card:hover .card-fade {
  opacity: 0.3;
}

@media (max-width: 768px) {
  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .sort-group {
    width: 100%;
  }

  .sort-select-wrapper {
    flex: 1;
  }

  .sort-select-wrapper select {
    width: 100%;
  }

  .article-card {
    padding: var(--spacing-md);
  }
}
</style>