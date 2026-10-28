<template>
  <div class="app-shell scanline-bg">
    <!-- 顶部导航栏 -->
    <header class="topbar">
      <div class="topbar-logo">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <circle cx="14" cy="14" r="13" stroke="#00b4ff" stroke-width="1.5"/>
          <path d="M8 14 L14 8 L20 14 L14 20 Z" fill="#00b4ff" opacity="0.8"/>
          <circle cx="14" cy="14" r="3" fill="#00b4ff"/>
        </svg>
        <span class="topbar-title">Smart Flow Analytics</span>
        <span class="topbar-sub">智慧客流分析平台</span>
      </div>

      <nav class="topbar-nav">
        <router-link to="/"        class="nav-item">📊 实时大屏</router-link>
        <router-link to="/zones"   class="nav-item">📐 展台分析</router-link>
        <router-link to="/cameras" class="nav-item">⚙️ 配置</router-link>
      </nav>

      <div class="topbar-status">
        <span class="badge badge-online pulse">
          <span>●</span> 系统运行中
        </span>
        <span class="topbar-time">{{ currentTime }}</span>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const currentTime = ref('')
let timer = null

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false,
  })
}

onMounted(() => { updateTime(); timer = setInterval(updateTime, 1000) })
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.app-shell {
  width: 100%; height: 100%;
  display: flex; flex-direction: column;
}

/* ── 顶部导航 ──────────────────────── */
.topbar {
  height: 56px;
  padding: 0 24px;
  background: rgba(10, 22, 40, 0.95);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 32px;
  backdrop-filter: blur(12px);
  flex-shrink: 0;
  z-index: 100;
}

.topbar-logo {
  display: flex; align-items: center; gap: 10px;
}
.topbar-title {
  font-size: 15px; font-weight: 700;
  color: var(--primary); letter-spacing: 0.02em;
}
.topbar-sub {
  font-size: 11px; color: var(--text-muted);
  padding-left: 10px; border-left: 1px solid var(--border);
}

.topbar-nav {
  display: flex; gap: 4px; margin-left: auto;
}
.nav-item {
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all var(--transition);
}
.nav-item:hover { color: var(--primary); background: var(--primary-dim); }
.nav-item.router-link-active {
  color: var(--primary);
  background: var(--primary-dim);
  border: 1px solid rgba(0,180,255,0.2);
}

.topbar-status {
  display: flex; align-items: center; gap: 12px; margin-left: 16px;
}
.topbar-time {
  font-size: 12px; color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

/* ── 主内容 ────────────────────────── */
.main-content {
  flex: 1; overflow: hidden;
}

/* ── 路由切换动效 ─────────────────── */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to       { opacity: 0; }
</style>
