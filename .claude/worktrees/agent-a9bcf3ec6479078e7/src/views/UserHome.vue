<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '@/api/request'

const userInfo = ref({
  id: 0,
  username: '',
  email: '',
  avatar: '',
  bio: '',
  article_count: 0
})
const loading = ref(true)

const fetchUserInfo = async () => {
  try {
    const response = await request.get('/home/')
    const data = response.data
    userInfo.value = {
      id: data.id || 0,
      username: data.username,
      email: data.email || '',
      avatar: data.avatar || '',
      bio: data.bio || '',
      article_count: data.article_count || 0
    }
  } catch (err) {
    console.error('获取用户信息失败:', err)
  }
}

onMounted(async () => {
  await fetchUserInfo()
  loading.value = false
})
</script>

<template>
  <div class="user-home-page">
    <div v-if="loading" class="loading-spinner">
      <div class="spinner-ring"></div>
      <span class="loading-text">加载中...</span>
    </div>
    <div v-else>
      <div class="profile-card">
        <div class="profile-cover"></div>
        <div class="profile-body">
          <div class="avatar-container">
            <img
              :src="userInfo.avatar || '/default-avatar.png'"
              :alt="userInfo.username"
              class="avatar"
            />
          </div>
          <h2 class="username">{{ userInfo.username }}</h2>
          <p class="email">{{ userInfo.email || '暂无邮箱' }}</p>
          <p class="bio" v-if="userInfo.bio">{{ userInfo.bio }}</p>
          <div class="stat-row">
            <div class="stat-item">
              <span class="stat-value">{{ userInfo.article_count }}</span>
              <span class="stat-label">文章</span>
            </div>
          </div>
          <router-link to="/profile" class="btn btn-primary edit-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            编辑资料
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-home-page {
  max-width: 600px;
  margin: 0 auto;
}

.profile-card {
  background: var(--color-card-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-elevated);
  overflow: hidden;
}

.profile-cover {
  height: 120px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.05));
  border-bottom: 1px solid var(--color-glass-border);
}

.profile-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 var(--spacing-xl) var(--spacing-2xl);
  margin-top: -50px;
}

.avatar-container {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  overflow: hidden;
  border: 4px solid var(--color-card-bg);
  box-shadow: var(--shadow-card);
  margin-bottom: var(--spacing-md);
}

.avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.username {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-primary);
  letter-spacing: -0.02em;
  margin-bottom: var(--spacing-xs);
}

.email {
  font-size: 0.85rem;
  color: var(--color-secondary);
  margin-bottom: var(--spacing-sm);
}

.bio {
  font-size: 0.9rem;
  color: var(--color-secondary);
  font-style: italic;
  margin-bottom: var(--spacing-lg);
  text-align: center;
  max-width: 400px;
}

.stat-row {
  display: flex;
  gap: var(--spacing-2xl);
  margin-bottom: var(--spacing-lg);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-value {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--color-primary);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--color-secondary);
  font-weight: 500;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.edit-btn {
  font-size: 0.85rem;
  padding: 8px 24px;
}

@media (max-width: 768px) {
  .profile-body {
    padding: 0 var(--spacing-lg) var(--spacing-xl);
  }

  .profile-cover {
    height: 80px;
  }
}
</style>
