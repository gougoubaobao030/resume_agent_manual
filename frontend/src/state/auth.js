import { reactive } from 'vue'

import { applyLocale, i18n } from '../i18n'
import {
  ApiError,
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  updatePreferredLanguage,
} from '../services/api'


export const auth = reactive({ initialized: false, user: null, status: 'idle', error: '' })

function applyAuthenticatedUser(user) {
  auth.user = user
  applyLocale(user.preferred_language)
}

export async function initializeAuth() {
  try {
    applyAuthenticatedUser(await getCurrentUser())
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) console.error('Initialize auth failed', error)
    auth.user = null
  } finally {
    auth.initialized = true
  }
}

export async function login(username, password) {
  auth.status = 'loading'
  auth.error = ''
  try {
    const user = await loginRequest(username, password)
    applyAuthenticatedUser(user)
    auth.status = 'success'
    return user
  } catch (error) {
    auth.status = 'error'
    auth.error = error.detail || 'Login failed'
    throw error
  }
}

export async function logout() {
  try {
    await logoutRequest()
  } finally {
    auth.user = null
    auth.status = 'idle'
    auth.error = ''
  }
}

export async function changeLocale(value) {
  const previous = i18n.global.locale.value
  applyLocale(value)
  if (!auth.user) return
  try {
    auth.user = await updatePreferredLanguage(value)
  } catch (error) {
    applyLocale(previous)
    throw error
  }
}
