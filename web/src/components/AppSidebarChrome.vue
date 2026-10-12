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
  diagnosticsActive: boolean
  usersActive: boolean
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
        :aria-label="expanded ? undefined : title"
      >
        <img
          src="/logo.svg"
          width="32"
          height="32"
          alt=""
          class="size-8 shrink-0 rounded-lg ring-1 ring-white/30"
        />
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
        <span
          class="inline-flex transition-transform duration-200 ease-in-out"
          :class="expanded ? 'rotate-180' : 'rotate-0'"
          aria-hidden="true"
        >
          <WlzIcon
            glyph="thisWay"
            size-class="text-lg"
            :tooltip="expanded ? t('shell.collapseSidebar') : t('shell.expandSidebar')"
          />
        </span>
      </button>
    </div>

    <nav
      class="flex min-h-0 flex-1 flex-col overflow-y-auto overflow-x-visible p-2"
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
                  :tooltip="t('inventories.nav')"
                />
                <span v-show="expanded" class="truncate">{{ t('inventories.nav') }}</span>
              </RouterLink>
            </div>
          </li>
          <li v-if="me?.isSuperuser">
            <div
              class="tooltip tooltip-right w-full"
              :class="{ 'before:hidden': expanded }"
              :data-tip="expanded ? undefined : t('users.nav')"
            >
              <RouterLink
                to="/users"
                :class="navItemClass(usersActive, expanded)"
                :aria-label="expanded ? undefined : t('users.nav')"
                :aria-current="usersActive ? 'page' : undefined"
              >
                <WlzIcon
                  glyph="gatherHere"
                  :active="usersActive"
                  size-class="text-lg"
                  :tooltip="t('users.nav')"
                />
                <span v-show="expanded">{{ t('users.nav') }}</span>
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
                :aria-label="expanded ? undefined : t('settings.heading')"
                :aria-current="settingsActive ? 'page' : undefined"
              >
                <WlzIcon
                  glyph="geheim"
                  :active="settingsActive"
                  size-class="text-lg"
                  :tooltip="t('settings.heading')"
                />
                <span v-show="expanded">{{ t('settings.heading') }}</span>
              </RouterLink>
            </div>
          </li>
          <li v-if="me?.isSuperuser">
            <div
              class="tooltip tooltip-right w-full"
              :class="{ 'before:hidden': expanded }"
              :data-tip="expanded ? undefined : t('diagnostics.nav')"
            >
              <RouterLink
                to="/diagnose"
                :class="navItemClass(diagnosticsActive, expanded)"
                :aria-label="expanded ? undefined : t('diagnostics.nav')"
                :aria-current="diagnosticsActive ? 'page' : undefined"
              >
                <WlzIcon
                  glyph="exchange"
                  :active="diagnosticsActive"
                  size-class="text-lg"
                  :tooltip="t('diagnostics.nav')"
                />
                <span v-show="expanded">{{ t('diagnostics.nav') }}</span>
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
                  :tooltip="ui.theme === 'light' ? t('theme.dark') : t('theme.light')"
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
                :aria-label="expanded ? undefined : t('auth.signOut')"
                @click="emit('signOut')"
              >
                <WlzIcon glyph="backToStart" size-class="text-lg" :tooltip="t('auth.signOut')" />
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
