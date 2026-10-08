<script setup lang="ts">
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchInstallationSettings } from '../api/settings'
import { fetchMe, logout } from '../api/me'
import { useUiStore } from '../stores/ui'

const { t } = useI18n()
const route = useRoute()
const queryClient = useQueryClient()
const ui = useUiStore()

const { data: settings } = useQuery({
  queryKey: ['settings'],
  queryFn: fetchInstallationSettings,
})

const { data: me } = useQuery({
  queryKey: ['me'],
  queryFn: fetchMe,
})

const title = computed(() => settings.value?.title ?? t('app.productName'))

watch(
  () => route.fullPath,
  () => {
    if (!ui.sidebarPinned) ui.closeSidebar()
  },
)

async function onSignOut() {
  await logout()
  await queryClient.invalidateQueries({ queryKey: ['me'] })
}

function navLinkClass(active: boolean) {
  return active ? 'active font-medium' : ''
}
</script>

<template>
  <div
    class="drawer min-h-screen bg-base-200"
    :class="{ 'lg:drawer-open': ui.sidebarPinned }"
  >
    <input
      id="app-drawer-toggle"
      v-model="ui.sidebarOpen"
      type="checkbox"
      class="drawer-toggle"
      :aria-label="t('shell.menu')"
    />

    <div class="drawer-content flex min-h-screen flex-col">
      <header class="navbar sticky top-0 z-20 border-b border-base-300/50 bg-base-100 shadow-sm">
        <div class="flex-none">
          <button
            type="button"
            class="btn btn-square btn-ghost"
            :class="{ 'lg:hidden': ui.sidebarPinned }"
            :aria-label="t('shell.menu')"
            @click="ui.toggleSidebar()"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="size-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
        </div>
        <div class="flex-1 px-2">
          <RouterLink to="/" class="text-lg font-semibold truncate">{{ title }}</RouterLink>
        </div>
        <div class="flex-none gap-1 pr-1">
          <button
            type="button"
            class="btn btn-ghost btn-sm btn-square"
            :aria-label="t('theme.toggle')"
            @click="ui.toggleTheme()"
          >
            <svg
              v-if="ui.theme === 'light'"
              xmlns="http://www.w3.org/2000/svg"
              class="size-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
              />
            </svg>
            <svg
              v-else
              xmlns="http://www.w3.org/2000/svg"
              class="size-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
              />
            </svg>
          </button>
          <a v-if="!me" class="btn btn-primary btn-sm" href="/login">
            {{ t('auth.signIn') }}
          </a>
          <button v-else type="button" class="btn btn-ghost btn-sm" @click="onSignOut">
            {{ t('auth.signOut') }}
          </button>
        </div>
      </header>

      <main class="flex-1">
        <RouterView />
      </main>
    </div>

    <div class="drawer-side z-30">
      <label for="app-drawer-toggle" class="drawer-overlay" :aria-label="t('shell.closeMenu')" />
      <aside class="flex min-h-full w-64 flex-col bg-base-100 text-base-content">
        <div class="border-b border-base-300/50 px-4 py-4">
          <p class="text-xs uppercase tracking-wide text-base-content/60">
            {{ t('app.productName') }}
          </p>
          <p class="font-semibold leading-tight">{{ title }}</p>
        </div>

        <nav class="flex-1 overflow-y-auto p-2">
          <ul class="menu w-full gap-1">
            <li>
              <RouterLink to="/" :class="navLinkClass(route.path === '/')">
                {{ t('nav.home') }}
              </RouterLink>
            </li>
            <li v-if="me">
              <RouterLink
                to="/inventories"
                :class="navLinkClass(route.path.startsWith('/inventories'))"
              >
                {{ t('inventories.nav') }}
              </RouterLink>
            </li>
          </ul>
        </nav>

        <div class="border-t border-base-300/50 p-2">
          <ul class="menu w-full gap-1">
            <li>
              <button type="button" @click="ui.toggleSidebarPinned()">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="size-5 shrink-0"
                  :class="{ 'text-primary': ui.sidebarPinned }"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M16 12V4h1V2H7v2h1v8l-2 2v2h10v-2l-2-2z"
                  />
                </svg>
                {{
                  ui.sidebarPinned ? t('shell.unpinSidebar') : t('shell.pinSidebar')
                }}
              </button>
            </li>
            <li>
              <button type="button" @click="ui.toggleTheme()">
                <svg
                  v-if="ui.theme === 'light'"
                  xmlns="http://www.w3.org/2000/svg"
                  class="size-5 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
                  />
                </svg>
                <svg
                  v-else
                  xmlns="http://www.w3.org/2000/svg"
                  class="size-5 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                  />
                </svg>
                {{ ui.theme === 'light' ? t('theme.dark') : t('theme.light') }}
              </button>
            </li>
          </ul>
        </div>
      </aside>
    </div>
  </div>
</template>
