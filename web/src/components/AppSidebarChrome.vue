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
  impersonating?: boolean
  inventories: Inventory[]
  inventoriesLoading?: boolean
  inventoriesListActive: boolean
  settingsActive: boolean
  diagnosticsActive: boolean
  usersActive: boolean
  myLoansActive: boolean
  calendarActive: boolean
  mobile?: boolean
}>()

const inventoryStore = useInventoryStore()

const emit = defineEmits<{ signOut: [] }>()

const { t } = useI18n()
const ui = useUiStore()

const showInstanceSection = computed(() => !!props.me)

const mutedBorderClass = computed(() =>
  props.impersonating ? 'border-vcp-blau/20' : 'border-white/15',
)

const sectionLabelClass = computed(() =>
  props.impersonating
    ? 'mb-1 px-2 text-xs font-medium uppercase tracking-wide text-vcp-blau/50'
    : 'mb-1 px-2 text-xs font-medium uppercase tracking-wide text-white/50',
)

function navItemClass(active: boolean, expanded: boolean) {
  if (props.impersonating) {
    return [
      'flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm no-underline transition-colors',
      expanded ? '' : 'justify-center',
      active
        ? 'bg-vcp-blau font-medium text-vcp-feuergelb'
        : 'text-vcp-blau/90 hover:bg-vcp-blau/10',
    ]
  }
  return [
    'flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm no-underline transition-colors',
    expanded ? '' : 'justify-center',
    active ? 'bg-white/15 font-medium text-white' : 'text-white/85 hover:bg-white/10',
  ]
}

const signOutLabel = computed(() =>
  props.impersonating ? t('impersonation.stop') : t('auth.signOut'),
)
</script>

<template>
  <div class="flex h-full min-h-0 flex-col" :class="impersonating ? 'text-vcp-blau' : 'text-white'">
    <div
      class="flex items-center gap-1 border-b p-2"
      :class="[mutedBorderClass, expanded ? 'justify-between' : 'flex-col gap-2']"
    >
      <RouterLink
        to="/"
        class="flex min-w-0 flex-1 items-center gap-2 no-underline"
        :class="[impersonating ? 'text-vcp-blau' : 'text-white', expanded ? '' : 'justify-center']"
        :aria-label="expanded ? undefined : title"
      >
        <img
          src="/logo.svg"
          width="32"
          height="32"
          alt=""
          class="size-8 shrink-0 rounded-lg ring-1"
          :class="impersonating ? 'ring-vcp-blau/30' : 'ring-white/30'"
        />
        <span v-show="expanded" class="truncate text-sm font-semibold leading-tight">{{ title }}</span>
      </RouterLink>
      <button
        v-if="!mobile"
        type="button"
        class="btn btn-ghost btn-sm btn-square shrink-0"
        :class="impersonating ? 'text-vcp-blau hover:bg-vcp-blau/10' : 'text-white hover:bg-white/10'"
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
        :impersonating="impersonating"
        :show-inventory-picker="!!me"
        :inventories="inventories"
        :inventories-loading="inventoriesLoading"
        :active-inventory-id="inventoryStore.activeInventoryId"
      />
    </nav>

    <div class="mt-auto space-y-2 border-t p-2" :class="mutedBorderClass">
      <div v-if="showInstanceSection">
        <p v-show="expanded" :class="sectionLabelClass">
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
          <li v-if="me?.isSuperuser || inventories.some((inventory) => inventory.canManage)">
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

      <div v-if="showInstanceSection" class="border-t" :class="mutedBorderClass" aria-hidden="true" />

      <div>
        <p v-show="expanded" :class="sectionLabelClass">
          {{ t('shell.sectionUser') }}
        </p>
        <ul class="space-y-1">
          <li v-if="me">
            <div
              class="tooltip tooltip-right w-full"
              :class="{ 'before:hidden': expanded }"
              :data-tip="expanded ? undefined : t('nav.calendar')"
            >
              <RouterLink
                to="/calendar"
                :class="navItemClass(calendarActive, expanded)"
                :aria-label="expanded ? undefined : t('nav.calendar')"
                :aria-current="calendarActive ? 'page' : undefined"
              >
                <WlzIcon
                  glyph="day"
                  :active="calendarActive"
                  size-class="text-lg"
                  :tooltip="t('nav.calendar')"
                />
                <span v-show="expanded" class="truncate">{{ t('nav.calendar') }}</span>
              </RouterLink>
            </div>
          </li>
          <li v-if="me">
            <div
              class="tooltip tooltip-right w-full"
              :class="{ 'before:hidden': expanded }"
              :data-tip="expanded ? undefined : t('nav.myLoans')"
            >
              <RouterLink
                to="/my-loans"
                :class="navItemClass(myLoansActive, expanded)"
                :aria-label="expanded ? undefined : t('nav.myLoans')"
                :aria-current="myLoansActive ? 'page' : undefined"
              >
                <WlzIcon
                  glyph="exchange"
                  :active="myLoansActive"
                  size-class="text-lg"
                  :tooltip="t('nav.myLoans')"
                />
                <span v-show="expanded" class="truncate">{{ t('nav.myLoans') }}</span>
              </RouterLink>
            </div>
          </li>
          <li v-if="me">
            <div
              class="tooltip tooltip-right w-full"
              :class="{ 'before:hidden': expanded }"
              :data-tip="expanded ? undefined : signOutLabel"
            >
              <button
                type="button"
                class="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm"
                :class="[
                  expanded ? '' : 'justify-center',
                  impersonating
                    ? 'bg-vcp-blau font-medium text-vcp-feuergelb hover:bg-vcp-blau/90'
                    : 'text-white/85 hover:bg-white/10',
                ]"
                :aria-label="expanded ? undefined : signOutLabel"
                @click="emit('signOut')"
              >
                <WlzIcon glyph="backToStart" size-class="text-lg" :tooltip="signOutLabel" />
                <span v-show="expanded">{{ signOutLabel }}</span>
              </button>
            </div>
          </li>
          <li v-else-if="expanded || mobile">
            <a
              href="/login"
              class="btn btn-sm w-full border-0"
              :class="
                impersonating
                  ? 'bg-vcp-blau text-vcp-feuergelb hover:bg-vcp-blau/90'
                  : 'bg-white text-vcp-blau hover:bg-white/90'
              "
            >
              {{ t('auth.signIn') }}
            </a>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
