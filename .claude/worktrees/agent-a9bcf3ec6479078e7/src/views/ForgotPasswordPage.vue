<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { userApi } from '@/api/user'
import { useRouter } from 'vue-router'

const router = useRouter()

const email = ref('')
const password = ref('')
const code = ref('')
const error = ref('')
const success = ref('')
const loading = ref(false)
const sendingCode = ref(false)
const codeSent = ref(false)
const countdown = ref(0)
let countdownInterval: number | undefined

onMounted(() => {
  // 确保loading状态初始化为false
  loading.value = false
  console.log('页面加载完成，loading状态:', loading.value)
})

const handleSendCode = async () => {
  if (!email.value) {
    error.value = '请输入邮箱'
    return
  }

  sendingCode.value = true
  error.value = ''
  
  try {
    await userApi.sendCode(email.value)
    codeSent.value = true
    startCountdown()
  } catch (err: unknown) {
    error.value = '发送验证码失败，请检查邮箱是否正确'
    console.error(err)
  } finally {
    sendingCode.value = false
  }
}

const startCountdown = () => {
  countdown.value = 60
  if (countdownInterval) {
    clearInterval(countdownInterval)
  }
  countdownInterval = window.setInterval(() => {
    if (countdown.value > 0) {
      countdown.value--
    } else {
      clearInterval(countdownInterval)
    }
  }, 1000)
}

const handleResetPassword = async () => {
  if (!email.value || !password.value || !code.value) {
    error.value = '请填写所有字段'
    return
  }

  loading.value = true
  error.value = ''
  success.value = ''
  console.log('开始重置密码，loading状态:', loading.value)
  
  try {
    await userApi.retrieve(email.value, password.value, code.value)
    success.value = '密码重置成功，请登录'
    setTimeout(() => {
      router.push('/login')
    }, 2000)
  } catch (err: unknown) {
    error.value = '密码重置失败，请检查验证码是否正确'
    console.error('重置密码错误:', err)
  } finally {
    loading.value = false
    console.log('重置密码完成，loading状态:', loading.value)
  }
}
</script>

<template>
  <div class="forgot-password-page">
    <div class="auth-container">
      <div class="auth-card">
        <div class="auth-header">
          <div class="auth-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
          </div>
          <h1 class="auth-title">重置密码</h1>
          <p class="auth-subtitle">输入邮箱获取验证码并设置新密码</p>
        </div>
        <form @submit.prevent="handleResetPassword" class="auth-form">
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
                :disabled="sendingCode || loading || countdown > 0"
                @click="handleSendCode"
              >
                {{ sendingCode ? '发送中...' : countdown > 0 ? `${countdown}s` : '发送验证码' }}
              </button>
            </div>
          </div>
          <div class="form-group">
            <label for="password">新密码</label>
            <input
              type="password"
              id="password"
              v-model="password"
              required
              :disabled="loading"
              class="input-field"
              placeholder="输入新密码"
            />
          </div>
          <div v-if="error" class="message-error">{{ error }}</div>
          <div v-if="success" class="message-success">{{ success }}</div>
          <button type="submit" class="btn btn-primary auth-submit" :disabled="loading">
            <span v-if="loading" class="spinner-ring" style="width:16px;height:16px;border-width:2px;"></span>
            <span v-else>{{ loading ? '重置中...' : '重置密码' }}</span>
          </button>
          <div class="auth-links">
            <router-link to="/login" class="auth-link">想起密码了？登录</router-link>
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
.forgot-password-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100dvh - 64px - 64px);
  padding: var(--spacing-xl);
}

.auth-container {
  position: relative;
  width: 100%;
  max-width: 440px;
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
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(124, 58, 237, 0.08));
  border-radius: var(--radius-card);
  color: #8B5CF6;
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
  background: radial-gradient(circle, rgba(139, 92, 246, 0.15), transparent);
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
  background: radial-gradient(circle, rgba(16, 185, 129, 0.08), transparent);
  bottom: 30%;
  right: -30px;
}

@media (max-width: 768px) {
  .forgot-password-page {
    padding: var(--spacing-md);
  }

  .auth-card {
    padding: var(--spacing-lg);
  }
}
</style>