<script setup lang="ts">
import { ref } from 'vue'
import { userApi } from '@/api/user'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'

const userStore = useUserStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const handleLogin = async () => {
  if (!username.value || !password.value) {
    error.value = '请输入用户名和密码'
    return
  }

  loading.value = true
  error.value = ''
  
  try {
    const response = await userApi.login({ username: username.value, password: password.value })
    console.log('登录响应:', response)
    userStore.login(response.data)
    router.push('/')
  } catch (err: unknown) {
    error.value = '登录失败，请检查您的凭据'
    console.error(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="auth-container">
      <div class="auth-card">
        <div class="auth-header">
          <div class="auth-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
              <polyline points="10 17 15 12 10 7"/>
              <line x1="15" y1="12" x2="3" y2="12"/>
            </svg>
          </div>
          <h1 class="auth-title">欢迎回来</h1>
          <p class="auth-subtitle">登录账户继续您的创作之旅</p>
        </div>
        <form @submit.prevent="handleLogin" class="auth-form">
          <div class="form-group">
            <label for="username">用户名</label>
            <input
              type="text"
              id="username"
              v-model="username"
              required
              :disabled="loading"
              class="input-field"
              placeholder="请输入用户名"
            />
          </div>
          <div class="form-group">
            <label for="password">密码</label>
            <input
              type="password"
              id="password"
              v-model="password"
              required
              :disabled="loading"
              class="input-field"
              placeholder="请输入密码"
            />
          </div>
          <div v-if="error" class="message-error">{{ error }}</div>
          <button type="submit" class="btn btn-primary auth-submit" :disabled="loading">
            <span v-if="loading" class="spinner-ring" style="width:16px;height:16px;border-width:2px;"></span>
            <span v-else>{{ loading ? '登录中...' : '登录' }}</span>
          </button>
          <div class="auth-links">
            <router-link to="/register" class="auth-link">还没有账户？注册</router-link>
            <router-link to="/forgot-password" class="auth-link muted">忘记密码？</router-link>
          </div>
        </form>
      </div>
      <div class="auth-decoration">
        <div class="decoration-shape shape-1"></div>
        <div class="decoration-shape shape-2"></div>
        <div class="decoration-shape shape-3"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100dvh - 64px - 64px);
  padding: var(--spacing-xl);
}

.auth-container {
  position: relative;
  width: 100%;
  max-width: 420px;
}

.auth-card {
  position: relative;
  z-index: 2;
  background: var(--color-card-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-elevated);
  padding: var(--spacing-2xl);
}

.auth-header {
  text-align: center;
  margin-bottom: var(--spacing-xl);
}

.auth-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto var(--spacing-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.08));
  border-radius: var(--radius-card);
  color: var(--color-accent);
}

.auth-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-primary);
  letter-spacing: -0.03em;
  margin-bottom: var(--spacing-xs);
}

.auth-subtitle {
  font-size: 0.9rem;
  color: var(--color-secondary);
  font-weight: 400;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-primary);
  letter-spacing: -0.01em;
}

.auth-submit {
  width: 100%;
  padding: 12px 20px;
  font-size: 0.95rem;
  margin-top: var(--spacing-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
}

.auth-links {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}

.auth-link {
  font-size: 0.85rem;
  color: var(--color-accent);
  text-decoration: none;
  font-weight: 500;
  transition: color var(--transition-fast);
}

.auth-link:hover {
  color: var(--color-accent-hover);
  text-decoration: underline;
}

.auth-link.muted {
  color: var(--color-secondary);
  font-weight: 400;
}

.auth-link.muted:hover {
  color: var(--color-accent);
}

/* Decoration */
.auth-decoration {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  overflow: hidden;
}

.decoration-shape {
  position: absolute;
  border-radius: 50%;
  opacity: 0.3;
}

.shape-1 {
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.15), transparent);
  top: -60px;
  right: -60px;
}

.shape-2 {
  width: 150px;
  height: 150px;
  background: radial-gradient(circle, rgba(16, 185, 129, 0.1), transparent);
  bottom: -40px;
  left: -40px;
}

.shape-3 {
  width: 100px;
  height: 100px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.08), transparent);
  bottom: 30%;
  right: -30px;
}

@media (max-width: 768px) {
  .login-page {
    padding: var(--spacing-md);
  }

  .auth-card {
    padding: var(--spacing-lg);
  }
}
</style>