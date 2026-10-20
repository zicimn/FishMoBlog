<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { articleApi, type ArticleDetailResponse } from '@/api/article'
import { useRouter } from 'vue-router'

const router = useRouter()

// 用户帖子列表
const userArticles = ref<ArticleDetailResponse[]>([])
const articlesLoading = ref(false)
const articlesError = ref('')

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)

const fetchUserArticles = async () => {
  articlesLoading.value = true
  articlesError.value = ''
  try {
    const response = await articleApi.getUserArticles(currentPage.value, pageSize.value)
    userArticles.value = response.data.articles
  } catch (err: unknown) {
    articlesError.value = '加载不出来'
    console.error(err)
  } finally {
    articlesLoading.value = false
  }
}

const handleEditArticle = (articleId: number) => {
  router.push(`/edit/${articleId}`)
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchUserArticles()
}

const handleDeleteArticle = async (articleId: number) => {
  if (!confirm('Are you sure you want to delete this article? This cannot be undone.')) {
    return
  }
  
  articlesLoading.value = true
  try {
    await articleApi.deleteArticle(articleId)
    // 删除成功后刷新页面
    await fetchUserArticles()
  } catch (err: unknown) {
    articlesError.value = '加载不出来'
    console.error(err)
  } finally {
    articlesLoading.value = false
  }
}

onMounted(() => {
  fetchUserArticles()
})
</script>

<template>
  <div class="user-articles-page">
    <div class="page-heading">
      <h1 class="page-title">我的文章</h1>
      <p class="page-subtitle">您创作的所有内容</p>
    </div>

    <div v-if="articlesLoading" class="loading-spinner">
      <div class="spinner-ring"></div>
      <span class="loading-text">加载文章中...</span>
    </div>

    <div v-else-if="articlesError" class="message-error">{{ articlesError }}</div>

    <div v-else-if="userArticles.length === 0" class="empty-state">
      <div class="empty-state-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      </div>
      <p class="empty-state-text">暂无文章</p>
    </div>

    <div v-else class="articles-list">
      <div v-for="article in userArticles" :key="article.id" class="article-card">
        <div class="article-info">
          <h3 class="article-title">{{ article.title }}</h3>
          <div class="article-meta">
            <span class="meta-item">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              {{ article.created_at ? new Date(article.created_at).toLocaleDateString() : '未知' }}
            </span>
            <span class="meta-tag">{{ article.category || '未分类' }}</span>
          </div>
        </div>
        <div class="article-actions">
          <router-link :to="`/article/${article.id}`" class="btn btn-ghost action-btn" v-if="article.id">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            查看
          </router-link>
          <button class="btn btn-ghost action-btn" @click="handleEditArticle(article.id!)" v-if="article.id">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            编辑
          </button>
          <button class="btn btn-ghost action-btn danger" @click="handleDeleteArticle(article.id!)" v-if="article.id">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          </button>
        </div>
      </div>

      <div class="pagination">
        <button class="pagination-btn" @click="handlePageChange(currentPage - 1)" :disabled="currentPage === 1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          上一页
        </button>
        <span class="pagination-info">{{ currentPage }}</span>
        <button class="pagination-btn" @click="handlePageChange(currentPage + 1)">
          下一页
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-articles-page {
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

.articles-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.article-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  background: var(--color-card-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  transition: all var(--transition-normal);
}

.article-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-elevated);
  border-color: rgba(59, 130, 246, 0.2);
}

.article-info {
  flex: 1;
  min-width: 0;
}

.article-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: var(--spacing-sm);
  letter-spacing: -0.02em;
}

.article-meta {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
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
}

.article-actions {
  display: flex;
  gap: var(--spacing-xs);
  flex-shrink: 0;
}

.action-btn {
  font-size: 0.8rem;
  padding: 6px 12px;
}

.action-btn.danger {
  color: var(--color-error);
  opacity: 0.6;
}

.action-btn.danger:hover {
  opacity: 1;
  background: rgba(225, 29, 72, 0.08);
  border-color: var(--color-error);
}

/* Pagination uses global styles */
</style>