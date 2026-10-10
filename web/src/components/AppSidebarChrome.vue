<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppSidebarNav from './AppSidebarNav.vue'
import WlzIcon from './WlzIcon.vue'
import type { Inventory } from '../schemas/inventory'
import type { Me } from '../schemas/me'
import { useInventoryStore } from '../stores/inventory'
import { useUiStore } from '../stores/ui'

const props = defineProps<{
  expanded: boolean
  title: string
  me?: Me | null
  inventories: Inventory[]
  inventoriesLoading?: boolean
  inventoriesListActive: boolean
  settingsActive: boolean
  mobile?: boolean
}>()

const inventoryStore = useInventoryStore()

const emit = defineEmits<{ signOut: [] }>()

const { t } = useI18n()
const ui = useUiStore()

const showInstanceSection = computed(() => !!props.me)

function navItemClass(active: boolean, expanded: boolean) {
  return [
    'flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm no-underline transition-colors',
    expanded ? '' : 'justify-center',
    active ? 'bg-white/15 font-medium text-white' : 'text-white/85 hover:bg-white/10',
  ]
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col text-white">
    <div
      class="flex items-center gap-1 border-b border-white/15 p-2"
      :class="expanded ? 'justify-between' : 'flex-col gap-2'"
    >
      <RouterLink
        to="/"
        class="flex min-w-0 flex-1 items-center gap-2 no-underline text-white"
        :class="expanded ? '' : 'justify-center'"
      >
        <img src="/favicon.svg" width="28" height="28" alt="" class="size-7 shrink-0" />
        <span v-show="expanded" class="truncate text-sm font-semibold leading-tight">{{ title }}</span>
      </RouterLink>
      <button
        v-if="!mobile"
        type="button"
        class="btn btn-ghost btn-sm btn-square shrink-0 text-white hover:bg-white/10"
        :title="expanded ? t('shell.collapseSidebar') : t('shell.expandSidebar')"
        :aria-label="expanded ? t('shell.collapseSidebar') : t('shell.expandSidebar')"
        @click="ui.toggleSidebarExpanded()"
      >
        <WlzIcon
          :glyph="expanded ? 'opposite' : 'thisWay'"
          size-class="text-lg"
        />
      </button>
    </div>

    <nav
      class="min-h-0 flex-1 overflow-y-auto p-2"
      :class="{ 'overflow-x-visible': !expanded }"
      :aria-label="t('shell.mainNav')"
    >
      <AppSidebarNav
        :expanded="expanded"
        :show-inventory-picker="!!me"
        :inventories="inventories"
        :inventories-loading="inventoriesLoading"
        :active-inventory-id="inventoryStore.activeInventoryId"
      />
    </nav>

    <div class="mt-auto space-y-2 border-t border-white/15 p-2">
      <div v-if="showInstanceSection">
        <p
          v-show="expanded"
          class="mb-1 px-2 text-xs font-medium uppercase tracking-wide text-white/50"
        >
          {{ t('shell.sectionInstance') }}
        </p>
        <ul class="space-y-1">
          <li v-if="me">
            <div
              class="tooltip tooltip-right w-full"
              :class="{ 'before:hidden': expanded }"
              :data-tip="expanded ? undefined : t('inventories.nav')"
            >
              <RouterLink
                to="/inventories"
                :class="navItemClass(inventoriesListActive, expanded)"
                :aria-label="expanded ? undefined : t('inventories.nav')"
                :aria-current="inventoriesListActive ? 'page' : undefined"
              >
                <WlzIcon
                  glyph="campPath"
                  :active="inventoriesListActive"
                  size-class="text-lg"
                />
                <span v-show="expanded" class="truncate">{{ t('inventories.nav') }}</span>
              </RouterLink>
            </div>
          </li>
          <li v-if="me?.isSuperuser">
            <div
              class="tooltip tooltip-right w-full"
              :class="{ 'before:hidden': expanded }"
              :data-tip="expanded ? undefined : t('settings.heading')"
            >
              <RouterLink
                to="/settings"
                :class="navItemClass(settingsActive, expanded)"
                :aria-current="settingsActive ? 'page' : undefined"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="size-4 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                  aria-hidden="true"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                <span v-show="expanded">{{ t('settings.heading') }}</span>
              </RouterLink>
            </div>
          </li>
        </ul>
      </div>

      <div v-if="showInstanceSection" class="border-t border-white/15" aria-hidden="true" />

      <div>
        <p
          v-show="expanded"
          class="mb-1 px-2 text-xs font-medium uppercase tracking-wide text-white/50"
        >
          {{ t('shell.sectionUser') }}
        </p>
        <ul class="space-y-1">
          <li>
            <div
              class="tooltip tooltip-right w-full"
              :class="{ 'before:hidden': expanded }"
              :data-tip="
                expanded ? undefined : ui.theme === 'light' ? t('theme.dark') : t('theme.light')
              "
            >
              <button
                type="button"
                class="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm text-white/85 hover:bg-white/10"
                :class="expanded ? '' : 'justify-center'"
                :aria-label="t('theme.toggle')"
                @click="ui.toggleTheme()"
              >
                <WlzIcon
                  :glyph="ui.theme === 'light' ? 'night' : 'day'"
                  size-class="text-lg"
                />
                <span v-show="expanded">
                  {{ ui.theme === 'light' ? t('theme.dark') : t('theme.light') }}
                </span>
              </button>
            </div>
          </li>
          <li v-if="me">
            <div
              class="tooltip tooltip-right w-full"
              :class="{ 'before:hidden': expanded }"
              :data-tip="expanded ? undefined : t('auth.signOut')"
            >
              <button
                type="button"
                class="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm text-white/85 hover:bg-white/10"
                :class="expanded ? '' : 'justify-center'"
                @click="emit('signOut')"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="size-4 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                  aria-hidden="true"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                  />
                </svg>
                <span v-show="expanded">{{ t('auth.signOut') }}</span>
              </button>
            </div>
          </li>
          <li v-else-if="expanded || mobile">
            <a href="/login" class="btn btn-sm w-full border-0 bg-white text-vcp-blau hover:bg-white/90">
              {{ t('auth.signIn') }}
            </a>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
