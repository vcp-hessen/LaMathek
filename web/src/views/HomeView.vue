<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, watchEffect } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchAuthMode } from '../api/authMode'
import { api } from '../api/client'
import { fetchInstallationSettings } from '../api/settings'
import { fetchMe } from '../api/me'
import ContextHelp from '../components/ContextHelp.vue'

type DashLoan = {
  id: number
  inventoryId: number
  inventoryName: string
  title: string
  phase: string
}

type Dashboard = {
  welcomeName: string
  canManage: boolean
  cards: Record<string, DashLoan[]>
}

const { t } = useI18n()
const { data: settings, isLoading: settingsLoading } = useQuery({
  queryKey: ['settings'],
  queryFn: fetchInstallationSettings,
})

const { data: authMode } = useQuery({
  queryKey: ['authMode'],
  queryFn: fetchAuthMode,
})

const { data: me, isLoading: meLoading } = useQuery({
  queryKey: ['me'],
  queryFn: fetchMe,
})

const { data: dashboard } = useQuery({
  queryKey: ['dashboard'],
  queryFn: async () => {
    const response = await api.get('/api/dashboard')
    return response.data as Dashboard
  },
  enabled: () => Boolean(me.value),
})

const displayName = computed(
  () => me.value?.name ?? me.value?.email ?? me.value?.sub ?? '',
)

const title = computed(() => settings.value?.title ?? t('app.productName'))
const subtitle = computed(() => settings.value?.subtitle ?? '')

const cardOrder = ['waiting', 'openRequests', 'returnsDue', 'overdue', 'openActions', 'myLoans'] as const

const visibleCards = computed(() => {
  if (dashboard.value?.canManage) return cardOrder
  return ['myLoans'] as const
})

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
      <a v-else class="btn btn-primary mt-4" href="/login">{{ t('auth.signIn') }}</a>
      <p v-if="authMode?.devBypass" class="mt-4 text-xs text-warning">
        {{ t('dev.authBypass') }}
      </p>
    </header>

    <div v-if="me && dashboard" class="grid gap-4 md:grid-cols-2">
      <section v-for="key in visibleCards" :key="key" class="rounded-lg border border-base-300 p-4">
        <h2 class="font-medium">
          {{ t(`dashboard.${key}`) }}
          <span class="opacity-60">({{ dashboard.cards[key]?.length ?? 0 }})</span>
        </h2>
        <ul class="mt-2 space-y-1 text-sm">
          <li v-for="loan in (dashboard.cards[key] ?? []).slice(0, 8)" :key="loan.id">
            <RouterLink :to="`/inventories/${loan.inventoryId}/loans/${loan.id}`">
              {{ loan.title || t('dashboard.untitled') }}
            </RouterLink>
            <span class="ml-2 text-xs opacity-60">{{ loan.inventoryName }}</span>
          </li>
        </ul>
      </section>
    </div>

    <nav v-if="me" class="mt-6 flex flex-wrap gap-3 text-sm">
      <RouterLink class="link" to="/my-loans">{{ t('loans.myLoansHeading') }}</RouterLink>
      <RouterLink class="link" to="/calendar">{{ t('nav.calendar') }}</RouterLink>
      <RouterLink class="link" to="/inventories">{{ t('inventories.nav') }}</RouterLink>
    </nav>
  </div>
</template>
