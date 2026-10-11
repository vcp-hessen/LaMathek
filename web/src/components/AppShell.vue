<script setup lang="ts">
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchInventories } from '../api/inventories'
import { fetchInstallationSettings } from '../api/settings'
import { fetchMe, logout } from '../api/me'
import AppBreadcrumbs from './AppBreadcrumbs.vue'
import AppFooter from './AppFooter.vue'
import AppSidebarChrome from './AppSidebarChrome.vue'
import { useInventoryStore } from '../stores/inventory'
import { useUiStore } from '../stores/ui'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const queryClient = useQueryClient()
const ui = useUiStore()
const inventoryStore = useInventoryStore()

const { data: settings } = useQuery({
  queryKey: ['settings'],
  queryFn: fetchInstallationSettings,
})

const { data: me } = useQuery({
  queryKey: ['me'],
  queryFn: fetchMe,
})

const { data: inventories, isLoading: inventoriesLoading } = useQuery({
  queryKey: ['inventories'],
  queryFn: fetchInventories,
  enabled: () => !!me.value,
})

const title = computed(() => settings.value?.title ?? t('app.productName'))
const inventoriesListActive = computed(
  () => route.path === '/inventories',
)
const settingsActive = computed(() => route.path === '/settings')
const usersActive = computed(() => route.path === '/users')

watch(
  () => route.fullPath,
  () => ui.closeMobileMenu(),
)

watch(
  () => [me.value, inventories.value] as const,
  ([user, list]) => {
    if (user && list) inventoryStore.reconcileWithAccessible(list)
  },
  { immediate: true },
)

const inventoryRouteNames = new Set([
  'inventory-material-types',
  'inventory-pieces',
  'inventory-stock',
  'inventory-sets',
  'inventory-loans',
  'loan-detail',
  'set-detail',
])

watch(
  () => [route.name, route.params.id] as const,
  ([name, rawId]) => {
    if (!name || !inventoryRouteNames.has(String(name))) return
    const num = Number(rawId)
    if (Number.isFinite(num)) inventoryStore.setActiveInventory(num)
  },
  { immediate: true },
)

async function onSignOut() {
  await logout()
  inventoryStore.setActiveInventory(null)
  await queryClient.cancelQueries()
  queryClient.clear()
  await router.push('/')
}
</script>

<template>
  <div class="flex min-h-screen bg-base-200">
    <Teleport to="body">
      <div
        v-if="ui.mobileMenuOpen"
        class="fixed inset-0 z-40 flex md:hidden"
        role="dialog"
        :aria-label="t('shell.menu')"
      >
        <button
          type="button"
          class="absolute inset-0 bg-black/40"
          :aria-label="t('shell.closeMenu')"
          @click="ui.closeMobileMenu()"
        />
        <aside
          class="relative flex h-full w-64 max-w-[85vw] flex-col border-r border-vcp-blau bg-vcp-blau shadow-xl"
        >
          <AppSidebarChrome
            :expanded="true"
            :title="title"
            :me="me"
            :inventories="inventories ?? []"
            :inventories-loading="inventoriesLoading"
            :inventories-list-active="inventoriesListActive"
            :settings-active="settingsActive"
            :users-active="usersActive"
            mobile
            @sign-out="onSignOut"
          />
        </aside>
      </div>
    </Teleport>

    <aside
      class="sticky top-0 z-10 hidden h-screen shrink-0 flex-col border-r border-vcp-blau bg-vcp-blau transition-[width] duration-200 md:flex"
      :class="ui.sidebarExpanded ? 'w-56' : 'w-14'"
    >
      <AppSidebarChrome
        :expanded="ui.sidebarExpanded"
        :title="title"
        :me="me"
        :inventories="inventories ?? []"
        :inventories-loading="inventoriesLoading"
        :inventories-list-active="inventoriesListActive"
        :settings-active="settingsActive"
        :users-active="usersActive"
        @sign-out="onSignOut"
      />
    </aside>

    <div class="flex min-h-screen min-w-0 flex-1 flex-col">
      <header class="navbar sticky top-0 z-20 border-b border-base-300/50 bg-base-100 shadow-sm">
        <div class="flex-none md:hidden">
          <button
            type="button"
            class="btn btn-square btn-ghost"
            :aria-label="t('shell.menu')"
            @click="ui.toggleMobileMenu()"
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
          <RouterLink to="/" class="btn btn-ghost btn-square" :aria-label="title">
            <img
              src="/logo.svg"
              width="32"
              height="32"
              alt=""
              class="size-8 rounded-lg"
            />
          </RouterLink>
        </div>
        <div class="flex min-w-0 flex-1 items-center gap-2 px-2 sm:gap-3">
          <AppBreadcrumbs class="min-w-0 flex-1" />
        </div>
        <div v-if="!me" class="flex-none pr-1 md:hidden">
          <a class="btn btn-primary btn-sm" href="/login">
            {{ t('auth.signIn') }}
          </a>
        </div>
      </header>

      <main class="flex-1">
        <RouterView />
      </main>
      <AppFooter :settings="settings" />
    </div>
  </div>
</template>
