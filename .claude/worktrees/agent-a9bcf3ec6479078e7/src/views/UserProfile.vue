<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { userApi } from '@/api/user'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'

const userStore = useUserStore()
const router = useRouter()

const newUsername = ref('')
const newEmail = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const newBio = ref('')

const error = ref('')
const success = ref('')
const loading = ref(false)

// 头像相关
const avatarUrl = ref('/upload/avatars/default_avatar.webp')
const avatarInput = ref<HTMLInputElement | null>(null)
const avatarLoading = ref(false)

const loadAvatar = async () => {
  try {
    const response = await userApi.getInfo()
    if (response.data && response.data.avatar) {
      avatarUrl.value = response.data.avatar + '?t=' + new Date().getTime()
    }
  } catch (err) {
    console.error('获取头像失败:', err)
  }
}

const handleAvatarChange = () => {
  if (avatarInput.value) {
    avatarInput.value.click()
  }
}

const handleAvatarFileSelect = async (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) {
    return
  }
  
  // 检查文件大小（不超过5MB）
  if (file.size > 5 * 1024 * 1024) {
    error.value = '头像文件大小不能超过5MB'
    return
  }
  
  // 检查文件类型
  if (!file.type.startsWith('image/')) {
    error.value = '请选择图片文件'
    return
  }
  
  avatarLoading.value = true
  error.value = ''
  
  try {
    // 将图片转换为 base64 格式
    const reader = new FileReader()
    reader.onload = async (e) => {
      const base64Data = e.target?.result as string
      if (!base64Data) {
        error.value = '图片读取失败'
        avatarLoading.value = false
        return
      }
      
      try {
        const response = await userApi.updateAvatar(base64Data)
        if (response.data && response.data.user && response.data.user.avatar) {
          avatarUrl.value = response.data.user.avatar + '?t=' + new Date().getTime()
          success.value = '头像更新成功'
        }
      } catch (err: unknown) {
        error.value = '更新头像失败'
        console.error('更新头像失败:', err)
      } finally {
        avatarLoading.value = false
      }
    }
    reader.onerror = () => {
      error.value = '图片读取失败'
      avatarLoading.value = false
    }
    reader.readAsDataURL(file)
  } catch (err: unknown) {
    error.value = '更新头像失败'
    console.error('更新头像失败:', err)
    avatarLoading.value = false
  }
}

const handleUpdate = async () => {
  if (newPassword.value && newPassword.value !== confirmPassword.value) {
    error.value = '新密码不匹配'
    return
  }

  loading.value = true
  error.value = ''
  success.value = ''
  
  try {
      const data = {
        new_username: newUsername.value || undefined,
        new_email: newEmail.value || undefined,
        new_password: newPassword.value || undefined,
        new_bio: newBio.value || undefined
      }
      console.log('发送的更新数据:', data)
      const response = await userApi.update(data)
      console.log('后端返回的响应:', response)
      console.log('响应数据:', response.data)
      success.value = '资料更新成功'
      // 重新登录以更新用户信息
      if (newUsername.value) {
        userStore.username = newUsername.value
      }
    } catch (err: unknown) {
      console.error('更新资料失败:', err)
      error.value = '更新资料失败'
    } finally {
      loading.value = false
    }
}

const handleDeleteAccount = async () => {
  if (!confirm('您确定要删除您的账户吗？此操作不可撤销。')) {
    return
  }

  loading.value = true
  error.value = ''
  success.value = ''
  
  try {
    await userApi.delete(true)
    userStore.logout()
    router.push('/')
  } catch (err: unknown) {
    error.value = '删除账户失败'
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAvatar()
})
</script>

<template>
  <div class="user-profile">
    <div class="page-heading">
      <h1 class="page-title">用户中心</h1>
      <p class="page-subtitle">管理您的账户信息</p>
    </div>

    <!-- Avatar Section -->
    <div class="glass-card avatar-section">
      <div class="avatar-display">
        <div class="avatar-wrapper">
          <img
            :src="avatarUrl"
            alt="头像"
            class="avatar"
            :class="{ loading: avatarLoading }"
          />
          <div class="avatar-overlay" @click="handleAvatarChange" v-if="!avatarLoading">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
          </div>
          <div v-if="avatarLoading" class="avatar-loading-overlay">
            <div class="spinner-ring" style="width:24px;height:24px;border-width:2px;"></div>
          </div>
        </div>
        <input ref="avatarInput" type="file" accept="image/*" style="display:none;" @change="handleAvatarFileSelect" />
        <p class="avatar-hint">点击更换头像 (jpg, png, webp, 最大 5MB)</p>
      </div>
    </div>

    <!-- Update Profile Form -->
    <div class="glass-card form-section">
      <h2 class="section-title">更新资料</h2>
      <form @submit.prevent="handleUpdate" class="update-form">
        <div class="form-row">
          <div class="form-group">
            <label for="newUsername">用户名</label>
            <input type="text" id="newUsername" v-model="newUsername" :disabled="loading" class="input-field" placeholder="新用户名（可选）" />
          </div>
          <div class="form-group">
            <label for="newEmail">邮箱</label>
            <input type="email" id="newEmail" v-model="newEmail" :disabled="loading" class="input-field" placeholder="新邮箱（可选）" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="newPassword">新密码</label>
            <input type="password" id="newPassword" v-model="newPassword" :disabled="loading" class="input-field" placeholder="留空不修改" />
          </div>
          <div class="form-group">
            <label for="confirmPassword">确认密码</label>
            <input type="password" id="confirmPassword" v-model="confirmPassword" :disabled="loading" class="input-field" placeholder="再次输入新密码" />
          </div>
        </div>
        <div class="form-group">
          <label for="newBio">个人简介</label>
          <textarea id="newBio" v-model="newBio" rows="3" :disabled="loading" class="input-field" placeholder="介绍一下自己..."></textarea>
        </div>
        <div v-if="error" class="message-error">{{ error }}</div>
        <div v-if="success" class="message-success">{{ success }}</div>
        <button type="submit" class="btn btn-primary form-submit" :disabled="loading">
          <span v-if="loading" class="spinner-ring" style="width:16px;height:16px;border-width:2px;"></span>
          <span v-else>{{ loading ? '更新中...' : '更新资料' }}</span>
        </button>
      </form>
    </div>

    <!-- Danger Zone -->
    <div class="glass-card danger-section">
      <h2 class="section-title danger-title">危险区域</h2>
      <p class="danger-desc">此操作不可撤销。您的账户和所有相关数据将被永久删除。</p>
      <button class="btn btn-danger" @click="handleDeleteAccount" :disabled="loading">
        {{ loading ? '处理中...' : '删除账户' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.user-profile {
  max-width: 700px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.page-heading {
  margin-bottom: 0;
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

.glass-card {
  background: var(--color-card-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  padding: var(--spacing-xl);
}

/* Avatar Section */
.avatar-section {
  display: flex;
  justify-content: center;
}

.avatar-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
}

.avatar-wrapper {
  position: relative;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  overflow: hidden;
  border: 3px solid var(--color-card-border);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.avatar-wrapper:hover {
  transform: scale(1.05);
  box-shadow: var(--shadow-elevated);
}

.avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: opacity var(--transition-fast);
}

.avatar.loading {
  opacity: 0.5;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity var(--transition-fast);
  color: white;
}

.avatar-wrapper:hover .avatar-overlay {
  opacity: 1;
}

.avatar-loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-hint {
  font-size: 0.75rem;
  color: var(--color-secondary);
  text-align: center;
}

/* Form Section */
.form-section {
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
}

.section-title {
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--color-primary);
  letter-spacing: -0.02em;
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-glass-border);
}

.update-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
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

.form-submit {
  width: 100%;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
}

/* Danger Zone */
.danger-section {
  border-color: rgba(225, 29, 72, 0.2);
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
}

.danger-title {
  color: var(--color-error);
  border-bottom-color: rgba(225, 29, 72, 0.15);
}

.danger-desc {
  font-size: 0.9rem;
  color: var(--color-secondary);
  margin-bottom: var(--spacing-lg);
  line-height: 1.5;
}

.danger-section .btn {
  width: 100%;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }

  .glass-card {
    padding: var(--spacing-lg);
  }
}
</style>