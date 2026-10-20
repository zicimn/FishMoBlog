<template>
  <div class="about-page">
    <div class="glass-card about-card">
      <div class="about-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="16" x2="12" y2="12"/>
          <line x1="12" y1="8" x2="12.01" y2="8"/>
        </svg>
      </div>
      <h1 class="about-title">关于我们</h1>
      <p class="about-desc">欢迎来到 Fish Platform，一个社区内容创作与分享平台。</p>
      <div class="about-divider"></div>
      <p class="about-text">
        我们致力于为用户提供优质的内容发布和社交体验。在这里，您可以撰写文章、分享链接、收藏喜欢的内容，并与社区互动。
      </p>
      <div class="about-features">
        <div class="feature-item">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          <span>Markdown 文章创作</span>
        </div>
        <div class="feature-item">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
          <span>链接分享与收藏</span>
        </div>
        <div class="feature-item">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <span>社区评论互动</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.about-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100dvh - 64px - 64px);
}

.about-card {
  max-width: 560px;
  text-align: center;
  padding: var(--spacing-2xl);
}

.about-icon {
  display: inline-flex;
  padding: var(--spacing-md);
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.08));
  border-radius: var(--radius-card);
  color: var(--color-accent);
  margin-bottom: var(--spacing-lg);
}

.about-title {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--color-primary);
  letter-spacing: -0.03em;
  margin-bottom: var(--spacing-md);
}

.about-desc {
  font-size: 1rem;
  color: var(--color-secondary);
  line-height: 1.6;
  margin-bottom: var(--spacing-lg);
}

.about-divider {
  width: 60px;
  height: 3px;
  background: linear-gradient(90deg, var(--color-accent), var(--color-accent-hover));
  border-radius: 3px;
  margin: 0 auto var(--spacing-lg);
}

.about-text {
  font-size: 0.9rem;
  color: var(--color-secondary);
  line-height: 1.7;
  margin-bottom: var(--spacing-xl);
}

.about-features {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  text-align: left;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-input-bg);
  border: 1px solid var(--color-glass-border);
  border-radius: var(--radius-sm);
  color: var(--color-primary);
  font-size: 0.9rem;
  font-weight: 500;
  transition: all var(--transition-fast);
}

.feature-item:hover {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

.feature-item svg {
  color: var(--color-accent);
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .about-card {
    padding: var(--spacing-lg);
  }
}
</style>
