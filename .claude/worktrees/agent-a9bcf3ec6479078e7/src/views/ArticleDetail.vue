<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { articleApi, type ArticleDetailResponse, type LinkRequest, type LinkResponse, type CommentRequest, type CommentResponse } from '@/api/article'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

// Markdown 解析器
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
})

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const articleId = ref(Number(route.params.id))
const article = ref<ArticleDetailResponse>({
  title: '',
  content: '',
  images: [],
  author_id: undefined,
  author_name: ''
})
const loading = ref(true)
const error = ref('')

// 渲染后的 Markdown 内容
const renderedContent = computed(() => {
  if (!article.value.content) return ''
  const html = md.render(article.value.content)
  return DOMPurify.sanitize(html)
})

// 链接相关
const links = ref<LinkResponse[]>([])
const linksLoading = ref(false)
const linksError = ref('')
const showLinks = ref(false)
const showAddLinkForm = ref(false)
const newLink = ref<LinkRequest>({
  url: '',
  title: ''
})
const addLinkLoading = ref(false)
const addLinkError = ref('')
const addLinkSuccess = ref('')

// 收藏相关
const isFavorite = ref(false)
const favoriteLoading = ref(false)

// 评论相关
const comments = ref<CommentResponse[]>([])
const commentsLoading = ref(false)
const commentsError = ref('')
const showComments = ref(true)
const newComment = ref<CommentRequest>({
  content: ''
})
const addCommentLoading = ref(false)
const addCommentError = ref('')
const addCommentSuccess = ref('')

const fetchArticle = async () => {
  loading.value = true
  error.value = ''
  try {
    console.log('Fetching article with id:', articleId.value)
    const response = await articleApi.visit(articleId.value)
    console.log('Article response:', response.data)
    console.log('Article images:', response.data.images)
    console.log('Article images type:', typeof response.data.images)
    console.log('Article images is array:', Array.isArray(response.data.images))
    article.value = response.data
  } catch (err: unknown) {
    console.error('Error loading article:', err)
    if (err instanceof Error) {
      error.value = `加载文章失败: ${err.message}`
    } else {
      error.value = '加载文章失败，请检查网络连接'
    }
  } finally {
    loading.value = false
  }
}

const fetchLinks = async () => {
  if (!showLinks.value) return
  
  linksLoading.value = true
  linksError.value = ''
  try {
    const response = await articleApi.getLinks(articleId.value)
    links.value = response.data.links
  } catch (err) {
    linksError.value = '加载不出来'
    console.error(err)
  } finally {
    linksLoading.value = false
  }
}

const fetchComments = async () => {
  if (!showComments.value) return
  
  commentsLoading.value = true
  commentsError.value = ''
  try {
    const response = await articleApi.getComments(articleId.value)
    comments.value = response.data.comments || []
  } catch (err) {
    commentsError.value = '加载不出来'
    console.error(err)
  } finally {
    commentsLoading.value = false
  }
}

const handleAddLink = async () => {
  if (!newLink.value.url) {
    addLinkError.value = '请输入链接地址'
    return
  }
  
  addLinkLoading.value = true
  addLinkError.value = ''
  addLinkSuccess.value = ''
  try {
    await articleApi.submitLink(articleId.value, newLink.value)
    addLinkSuccess.value = 'Link added successfully'
    newLink.value = {
      url: '',
      title: ''
    }
    // 重新获取链接列表
    await fetchLinks()
  } catch (err) {
    addLinkError.value = '加载不出来'
    console.error(err)
  } finally {
    addLinkLoading.value = false
  }
}

const handleAddComment = async () => {
  if (!newComment.value.content) {
    addCommentError.value = '请输入评论内容'
    return
  }
  
  addCommentLoading.value = true
  addCommentError.value = ''
  addCommentSuccess.value = ''
  try {
    await articleApi.submitComment(articleId.value, newComment.value)
    addCommentSuccess.value = '评论发布成功'
    newComment.value = {
      content: ''
    }
    // 重新获取评论列表
    await fetchComments()
  } catch (err) {
    addCommentError.value = '发布评论失败'
    console.error(err)
  } finally {
    addCommentLoading.value = false
  }
}

const handleEdit = () => {
  router.push(`/edit/${articleId.value}`)
}

const toggleLinks = () => {
  showLinks.value = !showLinks.value
  if (showLinks.value) {
    fetchLinks()
  }
}

const handleFavorite = async () => {
  if (!userStore.isLoggedIn) {
    alert('请先登录')
    return
  }
  
  favoriteLoading.value = true
  
  try {
    if (isFavorite.value) {
      await articleApi.removeFavorite(articleId.value)
      isFavorite.value = false
    } else {
      await articleApi.addFavorite(articleId.value)
      isFavorite.value = true
    }
  } catch (err) {
    console.error('收藏操作失败:', err)
    alert('收藏操作失败')
  } finally {
    favoriteLoading.value = false
  }
}

const formatDate = (dateString: string): string => {
  try {
    const date = new Date(dateString)
    if (isNaN(date.getTime())) {
      return '未知时间'
    }
    return date.toLocaleString()
  } catch {
    return '未知时间'
  }
}

onMounted(() => {
  fetchArticle()
  fetchComments()
})
</script>

<template>
  <div class="article-detail">
    <div v-if="loading" class="loading-spinner">
      <div class="spinner-ring"></div>
      <span class="loading-text">加载中...</span>
    </div>
    <div v-else-if="error" class="message-error" style="max-width:600px;margin:0 auto;">{{ error }}</div>
    <div v-else class="article-content">
      <!-- Article Body -->
      <article class="article-body">
        <div class="article-header">
          <div>
            <h1 class="article-title">{{ article.title }}</h1>
            <div class="article-meta-line">
              <span v-if="article.author_name || article.author_id" class="meta-author">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                {{ article.author_name || article.author_id }}
              </span>
              <span v-if="article.views" class="meta-views">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                {{ article.views }}
              </span>
            </div>
          </div>
          <button
            v-if="userStore.isLoggedIn && article.author_id === userStore.id"
            class="btn btn-ghost edit-btn"
            @click="handleEdit"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            编辑
          </button>
        </div>

        <!-- Content -->
        <div class="markdown-body" v-html="renderedContent"></div>

        <!-- Images -->
        <div v-if="article.images && (typeof article.images === 'string' || (Array.isArray(article.images) && article.images.length > 0))" class="article-images">
          <img
            v-if="typeof article.images === 'string'"
            :src="article.images + '?t=' + new Date().getTime()"
            alt="Article image"
            class="article-image"
          />
          <img
            v-else-if="Array.isArray(article.images)"
            v-for="(image, index) in article.images"
            :key="index"
            :src="image + '?t=' + new Date().getTime()"
            alt="Article image"
            class="article-image"
          />
        </div>
      </article>

      <!-- Actions Bar -->
      <div class="actions-bar">
        <div class="actions-left">
          <button class="btn btn-ghost action-btn" @click="toggleLinks">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
            {{ showLinks ? '隐藏链接' : '显示链接' }}
          </button>
          <button class="btn btn-ghost action-btn" @click="showAddLinkForm = !showAddLinkForm">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            {{ showAddLinkForm ? '取消' : '添加链接' }}
          </button>
        </div>
        <button
          class="btn action-fav"
          :class="{ favorited: isFavorite }"
          @click="handleFavorite"
          :disabled="favoriteLoading"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" :fill="isFavorite ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
          {{ isFavorite ? '已收藏' : '收藏' }}
        </button>
      </div>

      <!-- Add Link Form -->
      <div v-if="showAddLinkForm" class="glass-card add-link-card">
        <h3 class="section-title">添加链接</h3>
        <div v-if="addLinkError" class="message-error">{{ addLinkError }}</div>
        <div v-if="addLinkSuccess" class="message-success">{{ addLinkSuccess }}</div>
        <div class="form-group">
          <label for="link-url">链接地址</label>
          <input type="url" id="link-url" v-model="newLink.url" placeholder="输入链接地址" :disabled="addLinkLoading" class="input-field" />
        </div>
        <div class="form-group">
          <label for="link-title">标题（可选）</label>
          <input type="text" id="link-title" v-model="newLink.title" placeholder="输入链接标题" :disabled="addLinkLoading" class="input-field" />
        </div>
        <button class="btn btn-primary" @click="handleAddLink" :disabled="addLinkLoading" style="width:100%;">
          {{ addLinkLoading ? '添加中...' : '添加链接' }}
        </button>
      </div>

      <!-- Links List -->
      <div v-if="showLinks" class="glass-card links-card">
        <h3 class="section-title">相关链接</h3>
        <div v-if="linksLoading" class="loading-spinner" style="padding:var(--spacing-lg);">
          <div class="spinner-ring" style="width:24px;height:24px;border-width:2px;"></div>
          <span class="loading-text" style="font-size:0.85rem;">加载链接中...</span>
        </div>
        <div v-else-if="linksError" class="message-error">{{ linksError }}</div>
        <div v-else-if="links.length === 0" class="empty-state" style="padding:var(--spacing-lg);">
          <p class="empty-state-text">暂无链接</p>
        </div>
        <div v-else class="links-list">
          <a v-for="link in links" :key="link.id" :href="link.url" target="_blank" rel="noopener noreferrer" class="link-item">
            <div class="link-info">
              <span class="link-title">{{ link.title || link.url }}</span>
              <span class="link-url-full">{{ link.url }}</span>
            </div>
            <svg class="link-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
          </a>
        </div>
      </div>

      <!-- Comments Section -->
      <div class="comments-section">
        <div class="glass-card comments-card">
          <h3 class="section-title">评论</h3>

          <!-- Comment Input -->
          <div class="comment-form">
            <textarea
              v-model="newComment.content"
              placeholder="写下你的评论..."
              rows="3"
              :disabled="addCommentLoading"
              class="input-field comment-textarea"
            ></textarea>
            <div class="comment-form-actions">
              <div v-if="!userStore.isLoggedIn" class="login-hint">
                <router-link to="/login">登录</router-link>后发表评论
              </div>
              <button
                class="btn btn-primary comment-submit"
                @click="handleAddComment"
                :disabled="addCommentLoading"
                v-if="userStore.isLoggedIn"
              >
                {{ addCommentLoading ? '发布中...' : '发表评论' }}
              </button>
            </div>
            <div v-if="addCommentError" class="message-error" style="margin-top:var(--spacing-sm);">{{ addCommentError }}</div>
            <div v-if="addCommentSuccess" class="message-success" style="margin-top:var(--spacing-sm);">{{ addCommentSuccess }}</div>
          </div>

          <!-- Comments List -->
          <div v-if="commentsLoading" class="loading-spinner" style="padding:var(--spacing-lg);">
            <div class="spinner-ring" style="width:24px;height:24px;border-width:2px;"></div>
            <span class="loading-text" style="font-size:0.85rem;">加载评论中...</span>
          </div>
          <div v-else-if="commentsError" class="message-error">{{ commentsError }}</div>
          <div v-else-if="comments.length === 0" class="empty-state" style="padding:var(--spacing-lg);">
            <p class="empty-state-text">暂无评论，快来发表第一条评论吧！</p>
          </div>
          <div v-else class="comments-list">
            <div v-for="(comment, index) in comments" :key="index" class="comment-item">
              <div class="comment-item-header">
                <div class="comment-avatar">{{ comment.name?.charAt(0)?.toUpperCase() || '?' }}</div>
                <div class="comment-meta">
                  <span class="comment-author">{{ comment.name }}</span>
                  <span class="comment-date">{{ formatDate(comment.created_at) }}</span>
                </div>
              </div>
              <div class="comment-body">{{ comment.content }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.article-detail {
  max-width: 860px;
  margin: 0 auto;
}

.article-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

/* Article Body */
.article-body {
  background: var(--color-card-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  padding: var(--spacing-2xl);
  transition: all var(--transition-normal);
}

.article-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--color-glass-border);
}

.article-title {
  font-size: 1.65rem;
  font-weight: 700;
  color: var(--color-primary);
  letter-spacing: -0.03em;
  line-height: 1.3;
  margin: 0;
}

.article-meta-line {
  display: flex;
  gap: var(--spacing-lg);
  margin-top: var(--spacing-sm);
}

.meta-author,
.meta-views {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.85rem;
  color: var(--color-secondary);
}

.edit-btn {
  flex-shrink: 0;
}

/* Article Images */
.article-images {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--spacing-md);
  margin-top: var(--spacing-xl);
}

.article-image {
  width: 100%;
  max-height: 350px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  transition: transform var(--transition-normal);
  cursor: zoom-in;
}

.article-image:hover {
  transform: scale(1.02);
}

/* Actions Bar */
.actions-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-card-bg);
  backdrop-filter: blur(24px);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}

.actions-left {
  display: flex;
  gap: var(--spacing-sm);
}

.action-btn {
  font-size: 0.85rem;
}

.action-fav {
  font-size: 0.85rem;
  background: transparent;
  color: var(--color-secondary);
  border: 1px solid var(--color-glass-border);
  padding: 8px 16px;
  border-radius: var(--radius-button);
  font-family: var(--font-stack);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.action-fav:hover:not(:disabled) {
  background: rgba(225, 29, 72, 0.06);
  border-color: var(--color-error);
  color: var(--color-error);
}

.action-fav.favorited {
  background: rgba(225, 29, 72, 0.08);
  border-color: var(--color-error);
  color: var(--color-error);
}

.action-fav:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Sections */
.section-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-primary);
  letter-spacing: -0.02em;
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-glass-border);
}

.add-link-card,
.links-card,
.comments-card {
  padding: var(--spacing-xl);
}

/* Links */
.links-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.link-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-input-bg);
  border: 1px solid var(--color-glass-border);
  border-radius: var(--radius-sm);
  text-decoration: none;
  transition: all var(--transition-fast);
}

.link-item:hover {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

.link-info {
  flex: 1;
  min-width: 0;
}

.link-title {
  display: block;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-primary);
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.link-url-full {
  font-size: 0.8rem;
  color: var(--color-secondary);
  word-break: break-all;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.link-arrow {
  flex-shrink: 0;
  color: var(--color-secondary);
  opacity: 0.4;
  transition: all var(--transition-fast);
}

.link-item:hover .link-arrow {
  opacity: 0.8;
  color: var(--color-accent);
  transform: translate(2px, -2px);
}

/* Comments */
.comments-section {
  margin-top: 0;
}

.comment-form {
  margin-bottom: var(--spacing-xl);
}

.comment-textarea {
  min-height: 100px;
  resize: vertical;
  font-family: var(--font-stack);
  line-height: 1.6;
}

.comment-form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--spacing-sm);
}

.login-hint {
  font-size: 0.85rem;
  color: var(--color-secondary);
}

.login-hint a {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: 500;
}

.login-hint a:hover {
  text-decoration: underline;
}

.comment-submit {
  font-size: 0.85rem;
  padding: 8px 20px;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.comment-item {
  padding: var(--spacing-lg);
  background: var(--color-input-bg);
  border: 1px solid var(--color-glass-border);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.comment-item:hover {
  border-color: rgba(59, 130, 246, 0.2);
  background: var(--color-card-bg);
}

.comment-item-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.comment-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-hover));
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  flex-shrink: 0;
}

.comment-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.comment-author {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-primary);
}

.comment-date {
  font-size: 0.75rem;
  color: var(--color-secondary);
}

.comment-body {
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--color-primary);
}

/* Form group within detail */
.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-primary);
}

@media (max-width: 768px) {
  .article-body {
    padding: var(--spacing-lg);
  }

  .article-header {
    flex-direction: column;
  }

  .article-title {
    font-size: 1.3rem;
  }

  .actions-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .actions-left {
    flex-wrap: wrap;
  }

  .action-btn,
  .action-fav {
    flex: 1;
    justify-content: center;
  }
}
</style>