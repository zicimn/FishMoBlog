<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const searchQuery = ref('')
const isDarkMode = ref(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
const showMyManage = ref(false)
const sidebarCollapsed = ref(false)
const mobileSidebarOpen = ref(false)

onMounted(() => {
  const token = localStorage.getItem('token')
  if (token) {
  }
})

const toggleDarkMode = () => {
  isDarkMode.value = !isDarkMode.value
}

const toggleMyManage = () => {
  showMyManage.value = !showMyManage.value
}

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

const toggleMobileSidebar = () => {
  mobileSidebarOpen.value = !mobileSidebarOpen.value
}

const closeMobileSidebar = () => {
  mobileSidebarOpen.value = false
}

const handleSearch = () => {
  if (searchQuery.value.trim()) {
    router.push(`/search/${searchQuery.value.trim()}`)
    searchQuery.value = ''
  }
}
</script>

<template>
  <div class="app" :class="{ 'dark-mode': isDarkMode }">
    <div class="layout">
      <!-- Mobile Overlay -->
      <transition name="overlay-fade">
        <div v-if="mobileSidebarOpen" class="mobile-overlay" @click="closeMobileSidebar"></div>
      </transition>

      <!-- Sidebar -->
      <aside class="sidebar" :class="{ collapsed: sidebarCollapsed, 'mobile-open': mobileSidebarOpen }">
        <div class="sidebar-header">
          <div class="brand">
            <div class="brand-icon">F</div>
            <span class="brand-text" :class="{ 'text-hidden': sidebarCollapsed }">Fish Platform</span>
          </div>
        </div>

        <nav class="sidebar-nav">
          <!-- Home -->
          <router-link to="/" class="nav-item" title="首页" @click="closeMobileSidebar">
            <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9 22 9 12 15 12 15 22"/>
            </svg>
            <span class="nav-label" :class="{ 'text-hidden': sidebarCollapsed }">首页</span>
            <span v-if="sidebarCollapsed" class="nav-tooltip">首页</span>
          </router-link>

          <!-- Publish -->
          <router-link to="/publish" class="nav-item" title="发布帖子" @click="closeMobileSidebar">
            <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>
            </svg>
            <span class="nav-label" :class="{ 'text-hidden': sidebarCollapsed }">发布帖子</span>
            <span v-if="sidebarCollapsed" class="nav-tooltip">发布帖子</span>
          </router-link>

          <!-- Divider -->
          <div class="nav-divider" :class="{ collapsed: sidebarCollapsed }">
            <span v-if="!sidebarCollapsed" class="divider-label">管理</span>
          </div>

          <!-- Logged-in Section -->
          <template v-if="userStore.isLoggedIn">
            <!-- My Management (collapsible group) -->
            <div class="nav-group">
              <button class="nav-item nav-toggle" title="我的管理" @click="toggleMyManage">
                <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
                  <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
                </svg>
                <span class="nav-label" :class="{ 'text-hidden': sidebarCollapsed }">我的管理</span>
                <svg v-if="!sidebarCollapsed" class="chevron" :class="{ open: showMyManage }" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
                <span v-if="sidebarCollapsed" class="nav-tooltip">我的管理</span>
              </button>
              <transition name="submenu-slide">
                <div v-if="showMyManage || sidebarCollapsed" class="nav-sublist" :class="{ collapsed: sidebarCollapsed }">
                  <template v-if="sidebarCollapsed">
                    <!-- In collapsed mode, show sub-items as separate top-level entries -->
                    <router-link to="/control" class="nav-item sub" title="帖子" @click="closeMobileSidebar">
                      <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
                        <polyline points="10 9 9 9 8 9"/>
                      </svg>
                      <span class="nav-label text-hidden">帖子</span>
                      <span class="nav-tooltip">帖子</span>
                    </router-link>
                    <router-link to="/favorite" class="nav-item sub" title="收藏" @click="closeMobileSidebar">
                      <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                      </svg>
                      <span class="nav-label text-hidden">收藏</span>
                      <span class="nav-tooltip">收藏</span>
                    </router-link>
                    <router-link to="/links" class="nav-item sub" title="链接" @click="closeMobileSidebar">
                      <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                      </svg>
                      <span class="nav-label text-hidden">链接</span>
                      <span class="nav-tooltip">链接</span>
                    </router-link>
                    <router-link to="/user-home" class="nav-item sub" title="个人" @click="closeMobileSidebar">
                      <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                        <circle cx="12" cy="7" r="4"/>
                      </svg>
                      <span class="nav-label text-hidden">个人</span>
                      <span class="nav-tooltip">个人</span>
                    </router-link>
                  </template>
                  <template v-else>
                    <router-link to="/control" class="nav-item sub" @click="closeMobileSidebar">
                      <span class="nav-dot"></span>
                      <span class="nav-label">帖子</span>
                    </router-link>
                    <router-link to="/favorite" class="nav-item sub" @click="closeMobileSidebar">
                      <span class="nav-dot"></span>
                      <span class="nav-label">收藏</span>
                    </router-link>
                    <router-link to="/links" class="nav-item sub" @click="closeMobileSidebar">
                      <span class="nav-dot"></span>
                      <span class="nav-label">链接</span>
                    </router-link>
                    <router-link to="/user-home" class="nav-item sub" @click="closeMobileSidebar">
                      <span class="nav-dot"></span>
                      <span class="nav-label">个人</span>
                    </router-link>
                  </template>
                </div>
              </transition>
            </div>

            <!-- Tools -->
            <router-link to="/tools" class="nav-item" title="工具" @click="closeMobileSidebar">
              <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
              </svg>
              <span class="nav-label" :class="{ 'text-hidden': sidebarCollapsed }">工具</span>
              <span v-if="sidebarCollapsed" class="nav-tooltip">工具</span>
            </router-link>

            <!-- Logout -->
            <button @click="userStore.logout()" class="nav-item logout" title="退出登录">
              <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              <span class="nav-label" :class="{ 'text-hidden': sidebarCollapsed }">退出登录</span>
              <span v-if="sidebarCollapsed" class="nav-tooltip">退出登录</span>
            </button>
          </template>

          <!-- Not Logged-in Section -->
          <template v-else>
            <div class="nav-divider" :class="{ collapsed: sidebarCollapsed }">
              <span v-if="!sidebarCollapsed" class="divider-label">账号</span>
            </div>

            <router-link to="/login" class="nav-item" title="登录" @click="closeMobileSidebar">
              <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
                <polyline points="10 17 15 12 10 7"/>
                <line x1="15" y1="12" x2="3" y2="12"/>
              </svg>
              <span class="nav-label" :class="{ 'text-hidden': sidebarCollapsed }">登录</span>
              <span v-if="sidebarCollapsed" class="nav-tooltip">登录</span>
            </router-link>
            <router-link to="/register" class="nav-item" title="注册" @click="closeMobileSidebar">
              <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="8.5" cy="7" r="4"/>
                <line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>
              </svg>
              <span class="nav-label" :class="{ 'text-hidden': sidebarCollapsed }">注册</span>
              <span v-if="sidebarCollapsed" class="nav-tooltip">注册</span>
            </router-link>
          </template>
        </nav>

        <!-- Collapse Toggle (desktop) -->
        <button class="sidebar-collapse-btn" @click="toggleSidebar" :title="sidebarCollapsed ? '展开侧栏' : '收起侧栏'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline :points="sidebarCollapsed ? '9 18 15 12 9 6' : '15 18 9 12 15 6'"/>
          </svg>
        </button>

        <!-- User Footer -->
        <div class="sidebar-footer" v-if="userStore.isLoggedIn" :class="{ collapsed: sidebarCollapsed }">
          <div class="user-chip" :title="userStore.username">
            <div class="chip-avatar">{{ userStore.username?.charAt(0)?.toUpperCase() || 'U' }}</div>
            <span class="chip-name" :class="{ 'text-hidden': sidebarCollapsed }">{{ userStore.username }}</span>
          </div>
        </div>
      </aside>

      <!-- Main Content -->
      <div class="main-area" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
        <header class="topbar">
          <div class="topbar-left">
            <!-- Mobile hamburger -->
            <button class="hamburger-btn" @click="toggleMobileSidebar" title="菜单">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="3" y1="6" x2="21" y2="6"/>
                <line x1="3" y1="12" x2="21" y2="12"/>
                <line x1="3" y1="18" x2="21" y2="18"/>
              </svg>
            </button>
            <span class="tagline">社区内容平台</span>
          </div>
          <div class="topbar-right">
            <div class="search-box">
              <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <input
                type="text"
                v-model="searchQuery"
                placeholder="搜索文章..."
                class="search-input"
                @keyup.enter="handleSearch"
              >
            </div>
            <button class="theme-toggle" @click="toggleDarkMode" :title="isDarkMode ? '切换亮色模式' : '切换暗色模式'">
              <svg v-if="!isDarkMode" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
              </svg>
              <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="5"/>
                <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
              </svg>
            </button>
          </div>
        </header>

        <main class="content">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </main>
      </div>
    </div>
  </div>
</template>

<style>
/* ===== CSS Custom Properties ===== */
:root {
  --color-primary: #18181B;
  --color-secondary: #71717A;
  --color-accent: #3B82F6;
  --color-accent-hover: #2563EB;
  --color-success: #10B981;
  --color-error: #E11D48;
  --color-bg: #FAFAF9;
  --color-card-bg: rgba(255, 255, 255, 0.7);
  --color-card-border: rgba(226, 232, 240, 0.5);
  --color-input-bg: rgba(255, 255, 255, 0.6);
  --color-input-border: rgba(148, 163, 184, 0.25);
  --color-sidebar-bg: rgba(255, 255, 255, 0.75);
  --color-sidebar-border: rgba(226, 232, 240, 0.6);
  --color-topbar-bg: rgba(250, 250, 249, 0.85);
  --color-topbar-border: rgba(226, 232, 240, 0.6);
  --color-hover: rgba(59, 130, 246, 0.08);
  --color-active: rgba(59, 130, 246, 0.12);
  --color-glass-border: rgba(226, 232, 240, 0.5);

  --radius-card: 1.25rem;
  --radius-input: 0.5rem;
  --radius-button: 0.5rem;
  --radius-sm: 0.375rem;
  --radius-full: 9999px;

  --shadow-card: 0 20px 40px -15px rgba(0, 0, 0, 0.05);
  --shadow-elevated: 0 25px 50px -12px rgba(0, 0, 0, 0.08);
  --shadow-button: 0 4px 6px -1px rgba(0, 0, 0, 0.05);

  --transition-base: cubic-bezier(0.16, 1, 0.3, 1);
  --transition-fast: 200ms var(--transition-base);
  --transition-normal: 300ms var(--transition-base);
  --transition-slow: 400ms var(--transition-base);

  --font-stack: 'Geist', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;

  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  --spacing-2xl: 48px;
  --spacing-3xl: 64px;

  --sidebar-width: 260px;
  --sidebar-collapsed-width: 68px;
  --topbar-height: 64px;
}

/* ===== Global Reset ===== */
*, *::before, *::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: var(--font-stack);
  line-height: 1.6;
  color: var(--color-primary);
  background: #FAFAF9;
  background-image:
    radial-gradient(ellipse at 15% 50%, rgba(59, 130, 246, 0.03) 0%, transparent 50%),
    radial-gradient(ellipse at 85% 20%, rgba(16, 185, 129, 0.02) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 80%, rgba(139, 92, 246, 0.02) 0%, transparent 50%);
  background-attachment: fixed;
  min-height: 100dvh;
}

/* ===== App Container ===== */
.app {
  min-height: 100dvh;
  transition: background var(--transition-normal);
}

/* ===== Dark Mode ===== */
.app.dark-mode {
  --color-primary: #F4F4F5;
  --color-secondary: #A1A1AA;
  --color-bg: #09090B;
  --color-card-bg: rgba(24, 24, 27, 0.8);
  --color-card-border: rgba(63, 63, 70, 0.5);
  --color-input-bg: rgba(24, 24, 27, 0.7);
  --color-input-border: rgba(63, 63, 70, 0.4);
  --color-sidebar-bg: rgba(9, 9, 11, 0.85);
  --color-sidebar-border: rgba(63, 63, 70, 0.5);
  --color-topbar-bg: rgba(9, 9, 11, 0.8);
  --color-topbar-border: rgba(63, 63, 70, 0.5);
  --color-hover: rgba(59, 130, 246, 0.12);
  --color-active: rgba(59, 130, 246, 0.18);
  --color-glass-border: rgba(63, 63, 70, 0.5);
  --shadow-card: 0 20px 40px -15px rgba(0, 0, 0, 0.3);
  --shadow-elevated: 0 25px 50px -12px rgba(0, 0, 0, 0.4);

  background: #09090B;
  background-image:
    radial-gradient(ellipse at 15% 50%, rgba(59, 130, 246, 0.05) 0%, transparent 50%),
    radial-gradient(ellipse at 85% 20%, rgba(16, 185, 129, 0.03) 0%, transparent 50%);
}

/* ===== Layout ===== */
.layout {
  display: flex;
  min-height: 100dvh;
  position: relative;
}

/* ===== Sidebar ===== */
.sidebar {
  width: var(--sidebar-width);
  background: var(--color-sidebar-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-right: 1px solid var(--color-sidebar-border);
  display: flex;
  flex-direction: column;
  padding: var(--spacing-lg);
  overflow-y: auto;
  overflow-x: hidden;
  flex-shrink: 0;
  position: relative;
  z-index: 20;
  transition: width var(--transition-normal), padding var(--transition-normal);
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
  padding: var(--spacing-lg) var(--spacing-sm);
}

/* Hide scrollbar for collapsed sidebar */
.sidebar.collapsed::-webkit-scrollbar {
  width: 0;
}

/* ===== Sidebar Header ===== */
.sidebar-header {
  display: flex;
  align-items: center;
  margin-bottom: var(--spacing-xl);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--color-sidebar-border);
  transition: border-color var(--transition-fast);
}

.sidebar.collapsed .sidebar-header {
  justify-content: center;
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  overflow: hidden;
}

.brand-icon {
  width: 34px;
  height: 34px;
  min-width: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3B82F6, #2563EB);
  color: white;
  font-size: 0.9rem;
  font-weight: 700;
  border-radius: var(--radius-sm);
  letter-spacing: -0.02em;
}

.brand-text {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--color-primary);
  letter-spacing: -0.02em;
  white-space: nowrap;
  transition: opacity var(--transition-fast), width var(--transition-fast);
}

/* ===== Sidebar Nav ===== */
.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

/* Nav item base */
.nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  text-decoration: none;
  color: var(--color-secondary);
  font-size: 0.9rem;
  font-weight: 500;
  transition: all var(--transition-fast);
  cursor: pointer;
  background: transparent;
  border: none;
  font-family: var(--font-stack);
  width: 100%;
  text-align: left;
  position: relative;
  white-space: nowrap;
  overflow: hidden;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 10px 0;
  border-radius: var(--radius-sm);
}

.nav-item:hover {
  background: var(--color-hover);
  color: var(--color-primary);
}

.nav-item.router-link-active {
  background: var(--color-active);
  color: var(--color-accent);
  font-weight: 600;
}

.nav-item.router-link-active::before {
  content: '';
  position: absolute;
  left: -24px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  border-radius: 0 3px 3px 0;
  background: var(--color-accent);
  transition: left var(--transition-normal);
}

.sidebar.collapsed .nav-item.router-link-active::before {
  left: -8px;
}

.nav-icon {
  flex-shrink: 0;
  opacity: 0.7;
  transition: opacity var(--transition-fast);
}

.nav-item:hover .nav-icon {
  opacity: 1;
}

.nav-item.router-link-active .nav-icon {
  opacity: 1;
  color: var(--color-accent);
}

.nav-label {
  flex: 1;
  overflow: hidden;
  transition: opacity var(--transition-fast), max-width var(--transition-fast);
}

.text-hidden {
  opacity: 0;
  width: 0;
  max-width: 0;
  overflow: hidden;
  flex: 0;
}

/* Tooltip for collapsed mode */
.nav-tooltip {
  position: absolute;
  left: calc(100% + 12px);
  top: 50%;
  transform: translateY(-50%);
  background: var(--color-primary);
  color: var(--color-bg);
  font-size: 0.8rem;
  font-weight: 500;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--transition-fast);
  z-index: 100;
  box-shadow: var(--shadow-elevated);
}

.nav-tooltip::before {
  content: '';
  position: absolute;
  right: 100%;
  top: 50%;
  transform: translateY(-50%);
  border: 5px solid transparent;
  border-right-color: var(--color-primary);
}

.sidebar.collapsed .nav-item:hover .nav-tooltip {
  opacity: 1;
}

/* Divider */
.nav-divider {
  height: 1px;
  background: var(--color-glass-border);
  margin: var(--spacing-md) 0;
  position: relative;
  transition: margin var(--transition-normal);
}

.nav-divider.collapsed {
  margin: var(--spacing-md) 0;
}

.divider-label {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  background: var(--color-sidebar-bg);
  padding-right: var(--spacing-sm);
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-secondary);
  opacity: 0.4;
}

/* Chevron */
.chevron {
  transition: transform var(--transition-fast);
  opacity: 0.4;
  flex-shrink: 0;
}

.chevron.open {
  transform: rotate(180deg);
}

/* Nav Group */
.nav-group {
  display: flex;
  flex-direction: column;
}

.nav-toggle {
  font-family: var(--font-stack);
}

/* Sublist - expanded mode */
.nav-sublist {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: 30px;
  overflow: hidden;
}

.nav-sublist.collapsed {
  padding-left: 0;
}

/* Sublist slide animation */
.submenu-slide-enter-active {
  transition: all 0.25s var(--transition-base);
  max-height: 200px;
}

.submenu-slide-leave-active {
  transition: all 0.2s var(--transition-base);
  max-height: 200px;
}

.submenu-slide-enter-from,
.submenu-slide-leave-to {
  max-height: 0;
  opacity: 0;
}

/* Sub items */
.nav-item.sub {
  font-size: 0.85rem;
  padding: 8px 12px;
}

/* Nav dot (sub-item indicator) */
.nav-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--color-secondary);
  flex-shrink: 0;
}

/* Logout */
.nav-item.logout {
  margin-top: auto;
  color: var(--color-error);
  opacity: 0.6;
}

.nav-item.logout:hover {
  opacity: 1;
  background: rgba(225, 29, 72, 0.08);
}

/* ===== Sidebar Collapse Button ===== */
.sidebar-collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 36px;
  background: transparent;
  border: 1px solid var(--color-glass-border);
  border-radius: var(--radius-sm);
  color: var(--color-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-top: auto;
  flex-shrink: 0;
}

.sidebar-collapse-btn:hover {
  background: var(--color-hover);
  color: var(--color-accent);
  border-color: var(--color-accent);
}

.sidebar.collapsed .sidebar-collapse-btn {
  border-color: transparent;
}

/* ===== Sidebar Footer ===== */
.sidebar-footer {
  padding-top: var(--spacing-md);
  transition: padding var(--transition-normal);
}

.sidebar-footer.collapsed {
  display: flex;
  justify-content: center;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  transition: all var(--transition-fast);
  overflow: hidden;
}

.sidebar.collapsed .user-chip {
  padding: 8px;
  justify-content: center;
}

.chip-avatar {
  width: 28px;
  height: 28px;
  min-width: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3B82F6, #2563EB);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  flex-shrink: 0;
}

.chip-name {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: opacity var(--transition-fast);
}

/* ===== Main Area ===== */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
  transition: margin-left var(--transition-normal);
}

/* ===== Topbar ===== */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-xl);
  background: var(--color-topbar-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-bottom: 1px solid var(--color-topbar-border);
  position: sticky;
  top: 0;
  z-index: 5;
  min-height: var(--topbar-height);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

/* Hamburger (mobile only) */
.hamburger-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: transparent;
  border: 1px solid var(--color-glass-border);
  border-radius: var(--radius-sm);
  color: var(--color-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.hamburger-btn:hover {
  background: var(--color-hover);
  color: var(--color-accent);
}

.tagline {
  font-size: 0.85rem;
  color: var(--color-secondary);
  font-weight: 500;
  letter-spacing: 0.02em;
  opacity: 0.5;
}

/* Theme Toggle (in topbar) */
.theme-toggle {
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

.theme-toggle:hover {
  background: var(--color-hover);
  color: var(--color-accent);
  border-color: var(--color-accent);
}

/* Search */
.search-box {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 8px 16px;
  background: var(--color-input-bg);
  border: 1px solid var(--color-input-border);
  border-radius: var(--radius-full);
  transition: all var(--transition-fast);
  width: 280px;
}

.search-box:focus-within {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  background: var(--color-card-bg);
}

.search-icon {
  flex-shrink: 0;
  color: var(--color-secondary);
  opacity: 0.5;
}

.search-input {
  border: none;
  background: transparent;
  outline: none;
  font-family: var(--font-stack);
  font-size: 0.875rem;
  color: var(--color-primary);
  width: 100%;
}

.search-input::placeholder {
  color: var(--color-secondary);
  opacity: 0.4;
}

/* ===== Content ===== */
.content {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-xl);
}

/* Page transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s var(--transition-base);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ===== Mobile Overlay ===== */
.mobile-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  z-index: 15;
}

.overlay-fade-enter-active,
.overlay-fade-leave-active {
  transition: opacity 0.3s var(--transition-base);
}
.overlay-fade-enter-from,
.overlay-fade-leave-to {
  opacity: 0;
}

/* ===== Shared Component Classes ===== */
.glass-card {
  background: var(--color-card-bg);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-radius: var(--radius-card);
  border: 1px solid var(--color-card-border);
  box-shadow: var(--shadow-card);
  padding: var(--spacing-xl);
  transition: all var(--transition-normal);
}

.glass-card:hover {
  box-shadow: var(--shadow-elevated);
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: 10px 20px;
  border-radius: var(--radius-button);
  font-family: var(--font-stack);
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: none;
  text-decoration: none;
  line-height: 1.2;
}

.btn-primary {
  background: var(--color-accent);
  color: white;
  box-shadow: var(--shadow-button);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
  transform: translateY(-1px);
  box-shadow: 0 6px 10px -2px rgba(59, 130, 246, 0.2);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-ghost {
  background: transparent;
  color: var(--color-secondary);
  border: 1px solid var(--color-glass-border);
}

.btn-ghost:hover:not(:disabled) {
  background: var(--color-hover);
  color: var(--color-primary);
  border-color: var(--color-accent);
}

.btn-danger {
  background: var(--color-error);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.btn-success {
  background: var(--color-success);
  color: white;
}

/* Inputs */
.input-field {
  padding: 10px 14px;
  border: 1px solid var(--color-input-border);
  border-radius: var(--radius-input);
  font-family: var(--font-stack);
  font-size: 0.9rem;
  color: var(--color-primary);
  background: var(--color-input-bg);
  transition: all var(--transition-fast);
  outline: none;
  width: 100%;
}

.input-field:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  background: var(--color-card-bg);
}

.input-field::placeholder {
  color: var(--color-secondary);
  opacity: 0.4;
}

.input-field:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Error / Success messages */
.message-error {
  color: var(--color-error);
  padding: 10px 14px;
  background: rgba(225, 29, 72, 0.06);
  border: 1px solid rgba(225, 29, 72, 0.15);
  border-radius: var(--radius-input);
  font-size: 0.85rem;
  text-align: center;
}

.message-success {
  color: var(--color-success);
  padding: 10px 14px;
  background: rgba(16, 185, 129, 0.06);
  border: 1px solid rgba(16, 185, 129, 0.15);
  border-radius: var(--radius-input);
  font-size: 0.85rem;
  text-align: center;
}

/* Loading */
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-3xl);
  gap: var(--spacing-md);
}

.spinner-ring {
  width: 36px;
  height: 36px;
  border: 3px solid var(--color-glass-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  color: var(--color-secondary);
  font-size: 0.9rem;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: var(--spacing-3xl) var(--spacing-xl);
  color: var(--color-secondary);
}

.empty-state-icon {
  font-size: 2.5rem;
  margin-bottom: var(--spacing-md);
  opacity: 0.3;
}

.empty-state-text {
  font-size: 0.95rem;
}

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  margin-top: var(--spacing-xl);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-glass-border);
}

.pagination-btn {
  padding: 8px 16px;
  border: 1px solid var(--color-glass-border);
  border-radius: var(--radius-button);
  background: var(--color-card-bg);
  color: var(--color-primary);
  font-family: var(--font-stack);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.pagination-btn:hover:not(:disabled) {
  background: var(--color-hover);
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination-info {
  font-size: 0.85rem;
  color: var(--color-secondary);
  font-weight: 500;
}

/* ===== Markdown content global styles ===== */
.markdown-body {
  line-height: 1.8;
  color: var(--color-primary);
  font-size: 1rem;
}

.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4 {
  margin-top: 1.5em;
  margin-bottom: 0.75em;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--color-primary);
}

.markdown-body h1 { font-size: 1.75rem; }
.markdown-body h2 { font-size: 1.4rem; }
.markdown-body h3 { font-size: 1.15rem; }

.markdown-body p {
  margin-bottom: 1em;
}

.markdown-body ul,
.markdown-body ol {
  padding-left: 1.5em;
  margin-bottom: 1em;
}

.markdown-body li {
  margin-bottom: 0.3em;
}

.markdown-body code {
  padding: 0.15em 0.4em;
  background: rgba(59, 130, 246, 0.06);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.875em;
  color: var(--color-accent);
}

.markdown-body pre {
  padding: var(--spacing-lg);
  background: rgba(24, 24, 27, 0.05);
  border-radius: var(--radius-sm);
  overflow-x: auto;
  margin-bottom: 1em;
  border: 1px solid var(--color-glass-border);
}

.app.dark-mode .markdown-body pre {
  background: rgba(255, 255, 255, 0.04);
}

.markdown-body pre code {
  background: transparent;
  padding: 0;
  color: var(--color-primary);
  font-size: 0.85em;
}

.markdown-body blockquote {
  border-left: 3px solid var(--color-accent);
  padding-left: var(--spacing-lg);
  margin-left: 0;
  margin-bottom: 1em;
  color: var(--color-secondary);
  font-style: italic;
}

.markdown-body a {
  color: var(--color-accent);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color var(--transition-fast);
}

.markdown-body a:hover {
  border-bottom-color: var(--color-accent);
}

.markdown-body hr {
  border: none;
  border-top: 1px solid var(--color-glass-border);
  margin: var(--spacing-xl) 0;
}

.markdown-body img {
  max-width: 100%;
  border-radius: var(--radius-sm);
  margin: var(--spacing-md) 0;
}

.markdown-body table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1em;
}

.markdown-body th,
.markdown-body td {
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--color-glass-border);
  text-align: left;
}

.markdown-body th {
  font-weight: 600;
  background: rgba(59, 130, 246, 0.04);
}

/* ===== Responsive ===== */
@media (max-width: 1024px) {
  .sidebar.collapsed {
    width: 60px;
    padding: var(--spacing-lg) 6px;
  }

  .search-box {
    width: 200px;
  }
}

@media (max-width: 768px) {
  /* Sidebar becomes off-canvas overlay on mobile */
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: var(--sidebar-width);
    z-index: 20;
    transform: translateX(-100%);
    transition: transform var(--transition-normal);
    border-right: 1px solid var(--color-sidebar-border);
    box-shadow: var(--shadow-elevated);
  }

  .sidebar.mobile-open {
    transform: translateX(0);
  }

  .sidebar.collapsed {
    width: var(--sidebar-width);
    padding: var(--spacing-lg);
  }

  .sidebar.collapsed .nav-item {
    justify-content: flex-start;
    padding: 10px 12px;
  }

  .sidebar.collapsed .nav-item .nav-label {
    opacity: 1;
    width: auto;
    max-width: none;
    flex: 1;
  }

  .sidebar.collapsed .nav-tooltip {
    display: none;
  }

  .sidebar.collapsed .nav-item.router-link-active::before {
    left: -24px;
  }

  .sidebar.collapsed .brand-text {
    opacity: 1;
    width: auto;
  }

  .sidebar.collapsed .sidebar-header {
    justify-content: flex-start;
  }

  .sidebar.collapsed .sidebar-footer {
    justify-content: flex-start;
  }

  .sidebar.collapsed .user-chip {
    justify-content: flex-start;
    padding: 8px 12px;
  }

  .sidebar.collapsed .sidebar-collapse-btn {
    border-color: var(--color-glass-border);
  }

  .sidebar.collapsed .nav-divider.collapsed {
    margin: var(--spacing-md) 0;
  }

  .sidebar.collapsed .nav-sublist {
    padding-left: 30px;
  }

  .sidebar.collapsed .nav-item.sub svg {
    display: none;
  }

  .sidebar.collapsed .nav-item.sub .nav-dot {
    display: inline-flex;
  }

  /* Re-show labels on mobile even in collapsed mode */
  .text-hidden {
    opacity: 1;
    width: auto;
    max-width: none;
    flex: 1;
    overflow: visible;
  }

  .mobile-overlay {
    display: block;
  }

  .hamburger-btn {
    display: flex;
  }

  .sidebar-collapse-btn {
    display: none;
  }

  .topbar {
    padding: 0 var(--spacing-md);
    min-height: 56px;
  }

  .search-box {
    width: 160px;
  }

  .search-box:focus-within {
    width: 200px;
  }

  .content {
    padding: var(--spacing-md);
  }

  .tagline {
    display: none;
  }
}

@media (max-width: 480px) {
  .search-box {
    width: 120px;
  }

  .search-box:focus-within {
    width: 160px;
  }

  .topbar-right {
    gap: var(--spacing-sm);
  }

  .content {
    padding: var(--spacing-sm);
  }
}
</style>

<style scoped>
/* Keep scoped styles minimal - most styles are global for shared components */
</style>
