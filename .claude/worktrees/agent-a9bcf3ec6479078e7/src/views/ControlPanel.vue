<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { articleApi } from '../api/article'
import type { UserArticleItem } from '../api/article'

const router = useRouter()

// 展开状态
const showArticles = ref(false)

// 文章相关
const userArticles = ref<UserArticleItem[]>([])
const articlesLoading = ref(false)
const articlesError = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

// 获取用户文章
const fetchUserArticles = async () => {
  if (!showArticles.value) return
  
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

// 切换文章展开状态
const toggleArticles = () => {
  showArticles.value = !showArticles.value
  if (showArticles.value) {
    fetchUserArticles()
  }
}

// 处理文章编辑
const handleEditArticle = (articleId: number) => {
  router.push(`/edit/${articleId}`)
}

// 处理文章查看
const handleViewArticle = (articleId: number) => {
  router.push(`/article/${articleId}`)
}

// 处理文章删除
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

// 分页处理
const handlePreviousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
    fetchUserArticles()
  }
}

const handleNextPage = () => {
  currentPage.value++
  fetchUserArticles()
}
</script>

<template>
  <div class="control-page">
    <div class="page-heading">
      <h1 class="page-title">我的文章</h1>
      <p class="page-subtitle">管理您的所有文章</p>
    </div>

    <div class="control-section">
      <button class="section-toggle" @click="toggleArticles">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
        {{ showArticles ? '隐藏文章' : '显示文章' }}
        <svg class="chevron" :class="{ open: showArticles }" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
      </button>

      <transition name="slide">
        <div v-if="showArticles" class="control-content">
          <div v-if="articlesLoading" class="loading-spinner" style="padding:var(--spacing-2xl);">
            <div class="spinner-ring"></div>
            <span class="loading-text">加载中...</span>
          </div>
          <div v-else-if="articlesError" class="message-error">{{ articlesError }}</div>
          <div v-else-if="userArticles.length === 0" class="empty-state" style="padding:var(--spacing-2xl);">
            <p class="empty-state-text">暂无文章</p>
          </div>
          <div v-else class="articles-list">
            <div v-for="article in userArticles" :key="article.id" class="article-card" @click="article.id && handleViewArticle(article.id)">
              <div class="article-info">
                <h3 class="article-title">{{ article.title }}</h3>
                <div class="article-meta">
                  <span class="meta-item">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                    {{ article.created_at ? new Date(article.created_at).toLocaleDateString() : '未知' }}
                  </span>
                  <span class="meta-tag">{{ article.category }}</span>
                </div>
                <div class="article-stats">
                  <span class="stat">{{ article.views }} views</span>
                  <span class="stat">{{ article.likes }} likes</span>
                </div>
              </div>
              <div class="article-actions" @click.stop>
                <button class="btn btn-ghost action-btn" @click="article.id && handleViewArticle(article.id)">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  查看
                </button>
                <button class="btn btn-ghost action-btn" @click="article.id && handleEditArticle(article.id)">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  编辑
                </button>
                <button class="btn btn-ghost action-btn danger" @click="article.id && handleDeleteArticle(article.id)">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </div>
            </div>

            <!-- Pagination -->
            <div class="pagination">
              <button class="pagination-btn" @click="handlePreviousPage" :disabled="currentPage === 1">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
                上一页
              </button>
              <span class="pagination-info">第 {{ currentPage }} 页</span>
              <button class="pagination-btn" @click="handleNextPage">下一页
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
              </button>
            </div>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<style scoped>
.control-page {
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

.control-section {
  margin-bottom: var(--spacing-xl);
}

.section-toggle {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  width: 100%;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-card-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  color: var(--color-primary);
  font-family: var(--font-stack);
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  text-align: left;
}

.section-toggle:hover {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

.chevron {
  margin-left: auto;
  transition: transform var(--transition-fast);
  opacity: 0.5;
}

.chevron.open {
  transform: rotate(180deg);
}

.control-content {
  margin-top: var(--spacing-md);
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
  cursor: pointer;
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
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

/* Slide transition */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.25s var(--transition-base);
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@media (max-width: 768px) {
  .article-card {
    flex-direction: column;
    align-items: stretch;
  }

  .article-actions {
    justify-content: flex-end;
  }
}
</style>