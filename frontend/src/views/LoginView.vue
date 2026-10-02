<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { auth, login } from '../state/auth'

const router = useRouter()
const { t } = useI18n()
const username = ref('')
const password = ref('')

async function handleSubmit() {
  try {
    await login(username.value, password.value)
    await router.replace('/')
  } catch {
    // auth.error 已保存后端错误。
  }
}
</script>

<template>
  <main class="login-page">
    <form class="login-card" @submit.prevent="handleSubmit">
      <div class="brand__mark">RA</div>
      <div><p class="eyebrow">Resume Agent</p><h1>{{ t('auth.login.title') }}</h1><p>{{ t('auth.login.description') }}</p></div>
      <label><span>{{ t('auth.login.username') }}</span><input v-model.trim="username" class="text-input" autocomplete="username" required /></label>
      <label><span>{{ t('auth.login.password') }}</span><input v-model="password" class="text-input" type="password" autocomplete="current-password" required /></label>
      <p v-if="auth.error" class="inline-message inline-message--error">{{ auth.error }}</p>
      <button class="button button--primary" :disabled="auth.status === 'loading'">{{ t(auth.status === 'loading' ? 'auth.login.loading' : 'auth.login.submit') }}</button>
    </form>
  </main>
</template>

<style scoped>
.login-page { min-height: 100vh; display: grid; place-items: center; padding: 24px; background: #eef2f7; }
.login-card { width: min(420px, 100%); display: grid; gap: 20px; padding: 36px; border-radius: 12px; background: #fff; box-shadow: 0 18px 50px rgba(22,39,65,.12); }
.login-card h1 { margin: 6px 0; }.login-card p { margin: 0; color: #64748b; }
.login-card label { display: grid; gap: 8px; font-size: .8rem; font-weight: 700; }
</style>
