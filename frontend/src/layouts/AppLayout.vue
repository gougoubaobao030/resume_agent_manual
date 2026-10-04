<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import { supportedLocales } from '../i18n'
import { auth, changeLocale, logout } from '../state/auth'
import { changePassword } from '../services/api'
import { initializeWorkspace, resetWorkspace, workspace } from '../state/workspace'

const route = useRoute()
const router = useRouter()
const { locale, t } = useI18n()
const mobileNavigationOpen = ref(false)
const isCollapsed = ref(false)
const currentPassword = ref('')
const newPassword = ref('')
const passwordMessage = ref('')
const passwordStatus = ref('idle')
const userInitial = computed(() => (auth.user?.display_name || auth.user?.username || 'U').slice(0, 1).toUpperCase())

onMounted(() => {
  void initializeWorkspace().catch((error) => {
    console.error('Initialize workspace failed', error)
  })
})

const navigation = [
  { name: 'dashboard', labelKey: 'layout.navigation.dashboard', mark: 'D', to: '/' },
  { name: 'jobs', labelKey: 'layout.navigation.jobs', mark: 'J', to: '/jobs' },
  { name: 'resumes', labelKey: 'layout.navigation.resumes', mark: 'U', to: '/resumes' },
  { name: 'candidates', labelKey: 'layout.navigation.candidates', mark: 'C', to: '/candidates' },
  { name: 'analysis', labelKey: 'layout.navigation.analysis', mark: 'A', to: '/analysis' },
]

const currentPage = computed(
  () => {
    const currentItem = navigation.find((item) => item.name === route.name)
    return t(currentItem?.labelKey ?? 'layout.navigation.candidateDetail')
  },
)

async function handleLocaleChange(event) {
  try {
    await changeLocale(event.target.value)
  } catch (error) {
    console.error('Save preferred language failed', error)
  }
}

async function handleLogout() {
  await logout()
  resetWorkspace()
  await router.replace('/login')
}

async function handlePasswordChange() {
  passwordStatus.value = 'loading'
  passwordMessage.value = ''
  try {
    auth.user = await changePassword(currentPassword.value, newPassword.value)
    currentPassword.value = ''
    newPassword.value = ''
    passwordStatus.value = 'success'
    passwordMessage.value = t('auth.password.success')
  } catch (error) {
    passwordStatus.value = 'error'
    passwordMessage.value = error.detail || t('auth.password.failed')
  }
}

function closeNavigation() {
  mobileNavigationOpen.value = false
}
</script>

<template>
  <div class="app-shell" :class="{ 'app-shell--collapsed': isCollapsed }">
    <aside class="sidebar" :class="{ 'sidebar--open': mobileNavigationOpen }">
      <div class="brand">
        <div class="brand__mark">RA</div>
        <div class="brand__text">
          <strong>Resume Agent</strong>
          <span>{{ t('layout.brandSubtitle') }}</span>
        </div>
      </div>

      <button
        class="sidebar__toggle"
        type="button"
        :aria-label="t(isCollapsed ? 'layout.navigation.expandHint' : 'layout.navigation.collapseHint')"
        :aria-expanded="!isCollapsed"
        @click="isCollapsed = !isCollapsed"
      >
        <span aria-hidden="true">{{ isCollapsed ? '»' : '«' }}</span>
        <span class="sidebar__toggle-label">
          {{ t(isCollapsed ? 'layout.navigation.expand' : 'layout.navigation.collapse') }}
        </span>
      </button>

      <nav class="primary-nav" :aria-label="t('layout.navigation.label')">
        <RouterLink
          v-for="item in navigation"
          :key="item.name"
          :to="item.to"
          class="primary-nav__item"
          :aria-label="t(item.labelKey)"
          :title="t(item.labelKey)"
          @click="closeNavigation"
        >
          <span class="primary-nav__mark" aria-hidden="true">{{ item.mark }}</span>
          <span class="primary-nav__label">{{ t(item.labelKey) }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar__footer">
        <span class="status-dot status-dot--muted"></span>
        <div>
          <strong>{{ t('layout.footer.phase') }}</strong>
          <span>{{ t('layout.footer.status') }}</span>
        </div>
      </div>
    </aside>

    <button
      v-if="mobileNavigationOpen"
      class="sidebar-backdrop"
      :aria-label="t('layout.navigation.closeHint')"
      @click="closeNavigation"
    ></button>

    <div class="workspace">
      <header class="topbar">
        <button
          class="mobile-menu"
          type="button"
          :aria-label="t('layout.navigation.openHint')"
          @click="mobileNavigationOpen = true"
        >
          <span></span><span></span><span></span>
        </button>
        <div>
          <p class="eyebrow">{{ t('layout.header.workbench') }}</p>
          <h1>{{ currentPage }}</h1>
        </div>
        <div class="topbar__actions">
          <span v-if="workspace.loading" class="status-badge status-badge--loading">{{ t('common.loading') }}</span>
          <label class="language-selector">
            <span class="visually-hidden">{{ t('layout.language.selectorLabel') }}</span>
            <select :value="locale" :aria-label="t('layout.language.selectorLabel')" @change="handleLocaleChange">
              <option
                v-for="item in supportedLocales"
                :key="item.value"
                :value="item.value"
              >
                {{ t(item.labelKey) }}
              </option>
            </select>
          </label>
          <details class="user-menu">
            <summary>
              <img v-if="auth.user?.avatar_path" class="user-avatar" :src="auth.user.avatar_path" alt="" />
              <span v-else class="user-avatar user-avatar--default">{{ userInitial }}</span>
              <span class="user-name">{{ auth.user?.display_name || auth.user?.username }}</span>
            </summary>
            <div class="user-menu__panel">
              <strong>{{ t('auth.password.title') }}</strong>
              <input v-model="currentPassword" class="text-input" type="password" :placeholder="t('auth.password.current')" autocomplete="current-password" />
              <input v-model="newPassword" class="text-input" type="password" :placeholder="t('auth.password.new')" autocomplete="new-password" />
              <small v-if="passwordMessage" :class="`message--${passwordStatus}`">{{ passwordMessage }}</small>
              <button class="button button--secondary button--small" type="button" :disabled="passwordStatus === 'loading' || newPassword.length < 8" @click="handlePasswordChange">{{ t('auth.password.submit') }}</button>
              <button class="danger-link" type="button" @click="handleLogout">{{ t('auth.logout') }}</button>
            </div>
          </details>
          <span class="phase-badge">MVP</span>
        </div>
      </header>

      <main class="page-container">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.user-menu { position: relative; }
.user-menu summary { display: flex; align-items: center; gap: 7px; cursor: pointer; list-style: none; }
.user-avatar { width: 30px; height: 30px; border-radius: 50%; object-fit: cover; }
.user-avatar--default { display: grid; place-items: center; color: white; background: #315b91; font-size: .75rem; font-weight: 800; }
.user-menu__panel { position: absolute; z-index: 30; top: calc(100% + 12px); right: 0; width: 270px; display: grid; gap: 10px; padding: 16px; border: 1px solid #dce3ec; border-radius: 9px; background: white; box-shadow: 0 14px 38px rgba(20,38,64,.16); }
.user-menu__panel small { font-size: .7rem; }.message--error { color: #b23b3b; }.message--success { color: #287752; }
</style>
