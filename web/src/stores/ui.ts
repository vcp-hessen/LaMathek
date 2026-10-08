import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_THEME = 'lamathek.theme'
const STORAGE_PINNED = 'lamathek.sidebarPinned'

export type AppTheme = 'light' | 'dark'

function readTheme(): AppTheme {
  const stored = localStorage.getItem(STORAGE_THEME)
  if (stored === 'light' || stored === 'dark') return stored
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark'
  return 'light'
}

export function applyTheme(theme: AppTheme) {
  document.documentElement.setAttribute('data-theme', theme)
}

export function initTheme() {
  applyTheme(readTheme())
}

export const useUiStore = defineStore('ui', () => {
  const theme = ref<AppTheme>(readTheme())
  const sidebarPinned = ref(localStorage.getItem(STORAGE_PINNED) === 'true')
  const sidebarOpen = ref(sidebarPinned.value)

  watch(
    theme,
    (value) => {
      applyTheme(value)
      localStorage.setItem(STORAGE_THEME, value)
    },
    { immediate: true },
  )

  watch(sidebarPinned, (pinned) => {
    localStorage.setItem(STORAGE_PINNED, pinned ? 'true' : 'false')
    if (pinned) sidebarOpen.value = true
  })

  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value
  }

  function closeSidebar() {
    sidebarOpen.value = false
  }

  function toggleSidebarPinned() {
    const next = !sidebarPinned.value
    sidebarPinned.value = next
    if (!next) sidebarOpen.value = false
  }

  return {
    theme,
    sidebarOpen,
    sidebarPinned,
    toggleTheme,
    toggleSidebar,
    closeSidebar,
    toggleSidebarPinned,
  }
})
