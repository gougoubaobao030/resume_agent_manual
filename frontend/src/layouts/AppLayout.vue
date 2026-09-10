<script setup>
import { computed, ref } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()
const mobileNavigationOpen = ref(false)

const navigation = [
  { name: 'dashboard', label: 'Dashboard', shortLabel: '首页', mark: 'D', to: '/' },
  { name: 'jobs', label: 'JD 管理', shortLabel: '岗位', mark: 'J', to: '/jobs' },
  { name: 'resumes', label: '简历导入', shortLabel: '导入', mark: 'U', to: '/resumes' },
  { name: 'candidates', label: '候选人列表', shortLabel: '候选人', mark: 'C', to: '/candidates' },
  { name: 'analysis', label: '分析结果', shortLabel: '分析', mark: 'A', to: '/analysis' },
]

const currentPage = computed(
  () => navigation.find((item) => item.name === route.name)?.label ?? '候选人详情',
)

function closeNavigation() {
  mobileNavigationOpen.value = false
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar" :class="{ 'sidebar--open': mobileNavigationOpen }">
      <div class="brand">
        <div class="brand__mark">RA</div>
        <div>
          <strong>Resume Agent</strong>
          <span>採用分析ワークスペース</span>
        </div>
      </div>

      <nav class="primary-nav" aria-label="主要导航">
        <RouterLink
          v-for="item in navigation"
          :key="item.name"
          :to="item.to"
          class="primary-nav__item"
          @click="closeNavigation"
        >
          <span class="primary-nav__mark" aria-hidden="true">{{ item.mark }}</span>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar__footer">
        <span class="status-dot status-dot--muted"></span>
        <div>
          <strong>MVP 开发阶段</strong>
          <span>后端状态将在下一阶段接入</span>
        </div>
      </div>
    </aside>

    <button
      v-if="mobileNavigationOpen"
      class="sidebar-backdrop"
      aria-label="关闭导航"
      @click="closeNavigation"
    ></button>

    <div class="workspace">
      <header class="topbar">
        <button
          class="mobile-menu"
          type="button"
          aria-label="打开导航"
          @click="mobileNavigationOpen = true"
        >
          <span></span><span></span><span></span>
        </button>
        <div>
          <p class="eyebrow">招聘初筛工作台</p>
          <h1>{{ currentPage }}</h1>
        </div>
        <div class="topbar__actions">
          <span class="language-label">中文</span>
          <span class="phase-badge">MVP</span>
        </div>
      </header>

      <main class="page-container">
        <RouterView />
      </main>
    </div>
  </div>
</template>
