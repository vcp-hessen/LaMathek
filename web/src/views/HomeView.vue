<script setup lang="ts">
import { useMe } from '../composables/useMe'
import { queryKeys } from '../api/queryKeys'
import { useQuery } from '@tanstack/vue-query'
import { computed, reactive, watchEffect } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchAuthMode } from '../api/authMode'
import { DASHBOARD_CARDS, fetchDashboard, type DashboardCard } from '../api/dashboard'
import { fetchInstallationSettings } from '../api/settings'
import ContextHelp from '../components/ContextHelp.vue'

const { t } = useI18n()
const route = useRoute()
const { data: settings, isLoading: settingsLoading } = useQuery({
  queryKey: queryKeys.settings,
  queryFn: fetchInstallationSettings,
})

const { data: authMode } = useQuery({
  queryKey: queryKeys.authMode,
  queryFn: fetchAuthMode,
})

const { data: me, isLoading: meLoading } = useMe()

const { data: dashboard } = useQuery({
  queryKey: queryKeys.dashboard,
  queryFn: fetchDashboard,
  enabled: () => Boolean(me.value),
})

const displayName = computed(
  () => me.value?.name ?? me.value?.email ?? me.value?.sub ?? '',
)

const title = computed(() => settings.value?.title ?? t('app.productName'))
const subtitle = computed(() => settings.value?.subtitle ?? '')

const CARD_PREVIEW = 8
const expanded = reactive<Partial<Record<DashboardCard, boolean>>>({})

/** Materialwart*innen see every card that has something; borrowers their own Verleihe. */
const visibleCards = computed<DashboardCard[]>(() => {
  if (!dashboard.value?.canManage) return ['myLoans']
  return DASHBOARD_CARDS.filter(
    (key) => (dashboard.value?.cards[key]?.length ?? 0) > 0 || !['conflicts', 'stuckMails'].includes(key),
  )
})

function cardLoans(key: DashboardCard) {
  const all = dashboard.value?.cards[key] ?? []
  return expanded[key] ? all : all.slice(0, CARD_PREVIEW)
}

watchEffect(() => {
  if (settings.value?.title) {
    document.title = settings.value.title
  }
})
</script>

<template>
  <div class="app-page">
    <header class="mb-6">
      <h1 class="text-3xl font-bold">
        {{ title }}
        <ContextHelp v-if="me" anchor="dashboard" />
      </h1>
      <p v-if="subtitle" class="text-base-content/70">{{ subtitle }}</p>
      <p v-if="settingsLoading || meLoading" class="text-sm">{{ t('auth.loading') }}</p>
      <p v-else-if="me" class="mt-2 text-lg">
        {{ t('auth.signedInAs', { name: displayName }) }}
      </p>
      <template v-else>
        <p v-if="route.query.sessionExpired" class="mt-2 text-sm text-warning">
          {{ t('app.sessionExpired') }}
        </p>
        <a class="btn btn-primary mt-4" href="/login">{{ t('auth.signIn') }}</a>
      </template>
      <p v-if="authMode?.devBypass" class="mt-4 text-xs text-warning">
        {{ t('dev.authBypass') }}
      </p>
    </header>

    <div v-if="me && dashboard" class="grid gap-4 md:grid-cols-2">
      <section
        v-for="key in visibleCards"
        :key="key"
        class="rounded-lg border p-4"
        :class="['conflicts', 'stuckMails'].includes(key) ? 'border-warning/60' : 'border-base-300'"
      >
        <h2 class="font-medium">
          {{ t(`dashboard.${key}`) }}
          <span class="opacity-60">({{ dashboard.cards[key]?.length ?? 0 }})</span>
        </h2>
        <ul class="mt-2 space-y-1 text-sm">
          <li v-for="loan in cardLoans(key)" :key="loan.id">
            <RouterLink :to="`/inventories/${loan.inventoryId}/loans/${loan.id}`">
              {{ loan.title || t('dashboard.untitled') }}
            </RouterLink>
            <span class="ml-2 text-xs opacity-60">{{ loan.inventoryName }}</span>
          </li>
        </ul>
        <button
          v-if="!expanded[key] && (dashboard.cards[key]?.length ?? 0) > CARD_PREVIEW"
          type="button"
          class="btn btn-ghost btn-xs mt-1"
          @click="expanded[key] = true"
        >
          {{ t('dashboard.showMore', { count: (dashboard.cards[key]?.length ?? 0) - CARD_PREVIEW }) }}
        </button>
      </section>
    </div>

    <nav v-if="me" class="mt-6 flex flex-wrap gap-3 text-sm">
      <RouterLink class="link" to="/my-loans">{{ t('loans.myLoansHeading') }}</RouterLink>
      <RouterLink class="link" to="/calendar">{{ t('nav.calendar') }}</RouterLink>
      <RouterLink class="link" to="/inventories">{{ t('inventories.nav') }}</RouterLink>
    </nav>
  </div>
</template>
