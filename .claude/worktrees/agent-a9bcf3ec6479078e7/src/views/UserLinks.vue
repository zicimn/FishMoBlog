<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { articleApi, type LinkResponse } from '@/api/article'

const links = ref<LinkResponse[]>([])
const linksLoading = ref(false)
const linksError = ref('')
const linksPage = ref(1)
const linksPageSize = ref(10)

const fetchUserLinks = async () => {
  linksLoading.value = true
  linksError.value = ''
  try {
    const response = await articleApi.getUserLinks(linksPage.value, linksPageSize.value)
    links.value = response.data.links
  } catch (err: unknown) {
    linksError.value = '加载不出来'
    console.error(err)
  } finally {
    linksLoading.value = false
  }
}

const handleDeleteLink = async (articleId: number, linkId: number) => {
  if (confirm('Are you sure you want to delete this link?')) {
    try {
      await articleApi.deleteUserLink(articleId, linkId)
      // Refresh links after deletion
      await fetchUserLinks()
    } catch (err: unknown) {
      console.error('删除链接失败:', err)
      linksError.value = '加载不出来'
    }
  }
}

onMounted(() => {
  fetchUserLinks()
})
</script>

<template>
  <div class="user-links-page">
    <div class="page-heading">
      <h1 class="page-title">我的链接</h1>
      <p class="page-subtitle">管理您分享的所有链接</p>
    </div>

    <div v-if="linksLoading" class="loading-spinner">
      <div class="spinner-ring"></div>
      <span class="loading-text">加载链接中...</span>
    </div>

    <div v-else-if="linksError" class="message-error">{{ linksError }}</div>

    <div v-else-if="links.length === 0" class="empty-state">
      <div class="empty-state-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
      </div>
      <p class="empty-state-text">暂无链接</p>
    </div>

    <div v-else class="links-container">
      <div v-for="link in links" :key="link.id" class="link-card">
        <div class="link-info">
          <h3 class="link-title">{{ link.title || link.url }}</h3>
          <a :href="link.url" target="_blank" rel="noopener noreferrer" class="link-url">
            {{ link.url }}
          </a>
          <span class="link-article">文章 ID: {{ link.article_id }}</span>
        </div>
        <button
          @click="handleDeleteLink(link.article_id, link.id)"
          class="btn btn-ghost action-btn danger"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          删除
        </button>
      </div>

      <div class="pagination">
        <button class="pagination-btn" @click="() => linksPage > 1 && linksPage-- && fetchUserLinks()" :disabled="linksPage === 1">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          上一页
        </button>
        <span class="pagination-info">第 {{ linksPage }} 页</span>
        <button class="pagination-btn" @click="() => linksPage++ && fetchUserLinks()">
          下一页
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-links-page {
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

.links-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.link-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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

.link-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-elevated);
  border-color: rgba(59, 130, 246, 0.2);
}

.link-info {
  flex: 1;
  min-width: 0;
}

.link-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: var(--spacing-xs);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.link-url {
  display: block;
  font-size: 0.85rem;
  color: var(--color-accent);
  text-decoration: none;
  margin-bottom: var(--spacing-xs);
  word-break: break-all;
  transition: color var(--transition-fast);
}

.link-url:hover {
  color: var(--color-accent-hover);
  text-decoration: underline;
}

.link-article {
  font-size: 0.8rem;
  color: var(--color-secondary);
}

.action-btn {
  font-size: 0.8rem;
  padding: 6px 12px;
  flex-shrink: 0;
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