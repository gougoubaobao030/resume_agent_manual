
// 注册i18n
import { createI18n } from 'vue-i18n'

import zhCN from './locales/zh-CN'
import jaJP from './locales/ja-JP'
import enUS from './locales/en-US'

// 统一管理可选语言
// 定义支持哪些语言
// 外部可以读取
// 不能给其他赋值
export const supportedLocales = [
  { value: 'zh-CN', label: '中文', labelKey: 'layout.language.zhCN' },
  { value: 'ja-JP', label: '日本語', labelKey: 'layout.language.jaJP' },
  { value: 'en-US', label: 'English', labelKey: 'layout.language.enUS' }
]

// 浏览器提供的上次存储功能
const savedLocale = localStorage.getItem('app-locale')


// 对照浏览器保存的日语看看能不能找出日语
// 不能的话就是变成中文
const browserLocale = navigator.language
function normalizeBrowserLocale(value) {
  if (supportedLocales.some((item) => item.value === value)) return value

  const language = value?.toLowerCase() ?? ''
  if (language === 'ja' || language.startsWith('ja-')) return 'ja-JP'
  if (language === 'en' || language.startsWith('en-')) return 'en-US'
  return null
}

const initialLocale = supportedLocales.some((item) => item.value === savedLocale)
  ? savedLocale
  : normalizeBrowserLocale(browserLocale) ?? 'zh-CN'


// 注册多语言管理器
export const i18n = createI18n({
  legacy: false, //使用 Composition API 模式，方便在 Vue 的 setup 中使用。
  globalInjection: true,
  locale: initialLocale, //当前选择的语言，初始化时优先读取浏览器保存的值。
  fallbackLocale: 'zh-CN', //缺少某个翻译时，回退到中文。
  messages: {
    'zh-CN': zhCN,
    'ja-JP': jaJP,
    'en-US': enUS
  }
})

export function applyLocale(value) {
  const locale = supportedLocales.some((item) => item.value === value) ? value : 'zh-CN'
  i18n.global.locale.value = locale
  localStorage.setItem('app-locale', locale)
  document.documentElement.lang = locale
}
