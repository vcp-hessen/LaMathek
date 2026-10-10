import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_THEME = 'lamathek.theme'
const STORAGE_EXPANDED = 'lamathek.sidebarExpanded'
const STORAGE_EXPANDED_LEGACY = 'lamathek.sidebarPinned'

export type AppTheme = 'light' | 'dark'

function readTheme(): AppTheme {
  const stored = localStorage.getItem(STORAGE_THEME)
  if (stored === 'light' || stored === 'dark') return stored
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark'
  return 'light'
}

function readSidebarExpanded(): boolean {
  const stored =
    localStorage.getItem(STORAGE_EXPANDED) ?? localStorage.getItem(STORAGE_EXPANDED_LEGACY)
  return stored === 'true'
}

export function applyTheme(theme: AppTheme) {
  document.documentElement.setAttribute('data-theme', theme)
}

export function initTheme() {
  applyTheme(readTheme())
}

export const useUiStore = defineStore('ui', () => {
  const theme = ref<AppTheme>(readTheme())
  const sidebarExpanded = ref(readSidebarExpanded())
  const mobileMenuOpen = ref(false)

  watch(
    theme,
    (value) => {
      applyTheme(value)
      localStorage.setItem(STORAGE_THEME, value)
    },
    { immediate: true },
  )

  watch(sidebarExpanded, (expanded) => {
    localStorage.setItem(STORAGE_EXPANDED, expanded ? 'true' : 'false')
  })

  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  function toggleSidebarExpanded() {
    sidebarExpanded.value = !sidebarExpanded.value
  }

  function toggleMobileMenu() {
    mobileMenuOpen.value = !mobileMenuOpen.value
  }

  function closeMobileMenu() {
    mobileMenuOpen.value = false
  }

  return {
    theme,
    sidebarExpanded,
    mobileMenuOpen,
    toggleTheme,
    toggleSidebarExpanded,
    toggleMobileMenu,
    closeMobileMenu,
  }
})
