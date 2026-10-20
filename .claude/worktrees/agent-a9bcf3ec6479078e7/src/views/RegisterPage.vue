<script setup lang="ts">
import { ref } from 'vue'
import { userApi } from '@/api/user'
import { useRouter } from 'vue-router'

const router = useRouter()

const name = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const code = ref('')
const error = ref('')
const success = ref('')
const loading = ref(false)
const countdown = ref(0)
const timer = ref<number | null>(null)

const startCountdown = () => {
  countdown.value = 60
  timer.value = window.setInterval(() => {
    if (countdown.value > 0) {
      countdown.value--
    } else {
      clearInterval(timer.value!)
    }
  }, 1000)
}

const handleSendCode = async () => {
  if (!email.value) {
    error.value = '请输入您的邮箱'
    return
  }

  try {
    await userApi.sendCode(email.value)
    success.value = '验证码发送成功'
    startCountdown()
  } catch (err: unknown) {
    error.value = '发送验证码失败'
    console.error(err)
  }
}

const handleRegister = async () => {
  if (!name.value || !email.value || !password.value || !confirmPassword.value || !code.value) {
    error.value = '请填写所有字段'
    return
  }

  if (password.value !== confirmPassword.value) {
    error.value = '密码不匹配'
    return
  }

  loading.value = true
  error.value = ''
  success.value = ''
  
  try {
    await userApi.register({ name: name.value, email: email.value, password: password.value, code: code.value })
    success.value = '注册成功！请登录。'
    // 跳转到登录页面
    setTimeout(() => {
      router.push('/login')
    }, 2000)
  } catch (err: unknown) {
    error.value = '注册失败，请重试'
    console.error(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-page">
    <div class="auth-container">
      <div class="auth-card">
        <div class="auth-header">
          <div class="auth-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="8.5" cy="7" r="4"/>
              <line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>
            </svg>
          </div>
          <h1 class="auth-title">创建账户</h1>
          <p class="auth-subtitle">加入社区，开始分享您的创作</p>
        </div>
        <form @submit.prevent="handleRegister" class="auth-form">
          <div class="form-group">
            <label for="name">用户名</label>
            <input
              type="text"
              id="name"
              v-model="name"
              required
              :disabled="loading"
              class="input-field"
              placeholder="输入用户名"
            />
          </div>
          <div class="form-group">
            <label for="email">邮箱</label>
            <input
              type="email"
              id="email"
              v-model="email"
              required
              :disabled="loading"
              class="input-field"
              placeholder="输入邮箱地址"
            />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="password">密码</label>
              <input
                type="password"
                id="password"
                v-model="password"
                required
                :disabled="loading"
                class="input-field"
                placeholder="输入密码"
              />
            </div>
            <div class="form-group">
              <label for="confirmPassword">确认密码</label>
              <input
                type="password"
                id="confirmPassword"
                v-model="confirmPassword"
                required
                :disabled="loading"
                class="input-field"
                placeholder="再次输入密码"
              />
            </div>
          </div>
          <div class="form-group">
            <label for="code">验证码</label>
            <div class="code-group">
              <input
                type="text"
                id="code"
                v-model="code"
                required
                :disabled="loading"
                class="input-field"
                placeholder="输入验证码"
              />
              <button
                type="button"
                class="btn btn-ghost code-btn"
                @click="handleSendCode"
                :disabled="loading || countdown > 0"
              >
                {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
              </button>
            </div>
          </div>
          <div v-if="error" class="message-error">{{ error }}</div>
          <div v-if="success" class="message-success">{{ success }}</div>
          <button type="submit" class="btn btn-primary auth-submit" :disabled="loading">
            <span v-if="loading" class="spinner-ring" style="width:16px;height:16px;border-width:2px;"></span>
            <span v-else>{{ loading ? '注册中...' : '注册' }}</span>
          </button>
          <div class="auth-links">
            <router-link to="/login" class="auth-link">已经有账户？登录</router-link>
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
.register-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100dvh - 64px - 64px);
  padding: var(--spacing-xl);
}

.auth-container {
  position: relative;
  width: 100%;
  max-width: 480px;
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
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(5, 150, 105, 0.08));
  border-radius: var(--radius-card);
  color: var(--color-success);
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

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
}

.code-group {
  display: flex;
  gap: var(--spacing-sm);
}

.code-group .input-field {
  flex: 1;
}

.code-btn {
  white-space: nowrap;
  flex-shrink: 0;
  font-size: 0.8rem;
  padding: 10px 16px;
}

.auth-submit {
  width: 100%;
  padding: 12px 20px;
  font-size: 0.95rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
}

.auth-links {
  display: flex;
  justify-content: center;
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
  background: radial-gradient(circle, rgba(16, 185, 129, 0.15), transparent);
  top: -60px;
  right: -60px;
}

.shape-2 {
  width: 150px;
  height: 150px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.1), transparent);
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
  .register-page {
    padding: var(--spacing-md);
  }

  .auth-card {
    padding: var(--spacing-lg);
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>