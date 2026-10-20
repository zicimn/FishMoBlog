<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '@/api/request'

interface Article {
  id: number
  title: string
  category: string
  created_at: string
  views: number
  likes: number
}

const router = useRouter()
const favorites = ref<Article[]>([])
const loading = ref(false)
const error = ref('')
const deletingId = ref<number | null>(null)

onMounted(async () => {
  await loadFavorites()
})

const loadFavorites = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await request.get('/user/favorite/get_list', {
      params: { page: 1, size: 10 }
    })
    const data = response.data
    favorites.value = data?.favorites || []
  } catch {
    error.value = '获取收藏失败'
  } finally {
    loading.value = false
  }
}

const goToArticle = (articleId: number) => {
  router.push(`/article/${articleId}`)
}

const removeFavorite = async (articleId: number, e: Event) => {
  e.stopPropagation()
  deletingId.value = articleId
  try {
    await request.delete(`/article/favorite/remove/${articleId}`)
    favorites.value = favorites.value.filter(item => item.id !== articleId)
  } catch {
    alert('删除失败')
  } finally {
    deletingId.value = null
  }
}
</script>

<template>
  <div class="favorite-page">
    <div class="page-heading">
      <h1 class="page-title">我的收藏</h1>
      <p class="page-subtitle">收藏您喜欢的文章</p>
    </div>

    <div v-if="loading" class="loading-spinner">
      <div class="spinner-ring"></div>
      <span class="loading-text">加载中...</span>
    </div>

    <div v-else-if="error" class="message-error">{{ error }}</div>

    <div v-else-if="favorites.length === 0" class="empty-state">
      <div class="empty-state-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
      </div>
      <p class="empty-state-text">暂无收藏</p>
    </div>

    <div v-else class="favorites-list">
      <div
        v-for="article in favorites"
        :key="article.id"
        class="fav-card"
        @click="goToArticle(article.id)"
      >
        <div class="fav-content">
          <h3 class="fav-title">{{ article.title }}</h3>
          <div class="fav-meta">
            <span class="meta-item">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              {{ new Date(article.created_at).toLocaleDateString() }}
            </span>
            <span class="meta-tag">{{ article.category }}</span>
          </div>
          <div class="fav-stats">
            <span class="stat">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              {{ article.views }}
            </span>
            <span class="stat">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>
              {{ article.likes }}
            </span>
          </div>
        </div>
        <button
          class="btn-icon remove-btn"
          @click="removeFavorite(article.id, $event)"
          :disabled="deletingId === article.id"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.favorite-page {
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

.favorites-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.fav-card {
  display: flex;
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

.fav-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-elevated);
  border-color: rgba(59, 130, 246, 0.2);
}

.fav-content {
  flex: 1;
  min-width: 0;
}

.fav-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: var(--spacing-sm);
  letter-spacing: -0.02em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fav-card:hover .fav-title {
  color: var(--color-accent);
}

.fav-meta {
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

.fav-stats {
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

.btn-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--color-glass-border);
  border-radius: var(--radius-sm);
  color: var(--color-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.btn-icon:hover:not(:disabled) {
  background: rgba(225, 29, 72, 0.06);
  border-color: var(--color-error);
  color: var(--color-error);
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>