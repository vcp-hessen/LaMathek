<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '../api/client'

type CalItem = {
  loanId: number
  inventoryId: number
  title: string
  phase: string
  pickupOn: string
  returnOn: string | null
  permanent: boolean
  mine: boolean
}

const props = defineProps<{
  inventoryId?: number
}>()

const { t } = useI18n()
const queryClient = useQueryClient()
const mode = ref<'month' | 'table'>('month')
const cursor = ref(new Date())

const path = computed(() =>
  props.inventoryId
    ? `/api/inventories/${props.inventoryId}/calendar`
    : '/api/me/calendar',
)

const { data, isLoading } = useQuery({
  queryKey: computed(() => ['calendar', path.value]),
  queryFn: async () => {
    const response = await api.get(path.value)
    return response.data as { items: CalItem[] }
  },
})

const items = computed(() => data.value?.items ?? [])

const monthLabel = computed(() =>
  cursor.value.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' }),
)

function shiftMonth(delta: number) {
  const next = new Date(cursor.value)
  next.setMonth(next.getMonth() + delta)
  cursor.value = next
}

function isoDate(date: Date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}
  const year = cursor.value.getFullYear()
  const month = cursor.value.getMonth()
  const first = new Date(year, month, 1)
  const startPad = (first.getDay() + 6) % 7
  const count = new Date(year, month + 1, 0).getDate()
  const cells: { date: Date | null; items: CalItem[] }[] = []
  for (let i = 0; i < startPad; i += 1) cells.push({ date: null, items: [] })
  for (let day = 1; day <= count; day += 1) {
    const date = new Date(year, month, day)
    const iso = isoDate(date)
    const hits = items.value.filter((item) => {
      const end = item.returnOn ?? item.pickupOn
      return item.pickupOn <= iso && iso <= end
    })
    cells.push({ date, items: hits })
  }
  return cells
})

const tokenMutation = useMutation({
  mutationFn: async () => {
    const url = props.inventoryId
      ? `/api/inventories/${props.inventoryId}/calendar-token`
      : '/api/me/calendar-token'
    const response = await api.post(url)
    return response.data as { path: string }
  },
  onSuccess: async () => {
    await queryClient.invalidateQueries({ queryKey: ['calendar'] })
  },
})

const feedUrl = computed(() => {
  const pathValue = tokenMutation.data.value?.path
  if (!pathValue) return ''
  return `${window.location.origin}${pathValue}`
})
</script>

<template>
  <div class="app-page">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold">{{ t('calendar.heading') }}</h1>
      <div class="flex gap-2">
        <button type="button" class="btn btn-sm" :class="mode === 'month' ? 'btn-primary' : ''" @click="mode = 'month'">
          {{ t('calendar.month') }}
        </button>
        <button type="button" class="btn btn-sm" :class="mode === 'table' ? 'btn-primary' : ''" @click="mode = 'table'">
          {{ t('calendar.table') }}
        </button>
      </div>
    </header>

    <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>

    <template v-else>
      <div v-if="mode === 'month'" class="mt-4">
        <div class="mb-2 flex items-center justify-between">
          <button type="button" class="btn btn-ghost btn-sm" @click="shiftMonth(-1)">‹</button>
          <span class="font-medium capitalize">{{ monthLabel }}</span>
          <button type="button" class="btn btn-ghost btn-sm" @click="shiftMonth(1)">›</button>
        </div>
        <div class="grid grid-cols-7 gap-px bg-base-300 text-xs">
          <div v-for="(cell, index) in days" :key="index" class="min-h-20 bg-base-100 p-1">
            <template v-if="cell.date">
              <div class="opacity-60">{{ cell.date.getDate() }}</div>
              <RouterLink
                v-for="item in cell.items"
                :key="item.loanId"
                class="mt-1 block truncate rounded px-1"
                :class="item.mine ? 'bg-vcp-blau text-white' : 'bg-base-200'"
                :to="`/inventories/${item.inventoryId}/loans/${item.loanId}`"
              >
                {{ item.title }}
              </RouterLink>
            </template>
          </div>
        </div>
      </div>

      <table v-else class="mt-4 w-full text-sm">
        <thead>
          <tr class="text-left">
            <th>{{ t('calendar.colTitle') }}</th>
            <th>{{ t('calendar.colFrom') }}</th>
            <th>{{ t('calendar.colTo') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.loanId">
            <td>
              <RouterLink :to="`/inventories/${item.inventoryId}/loans/${item.loanId}`">
                {{ item.title }}
              </RouterLink>
              <span v-if="item.permanent" class="ml-2 text-xs opacity-70">{{ t('loans.kindPermanent') }}</span>
            </td>
            <td>{{ item.pickupOn }}</td>
            <td>{{ item.returnOn ?? '—' }}</td>
          </tr>
        </tbody>
      </table>

      <section class="mt-6 text-sm">
        <button type="button" class="btn btn-outline btn-sm" @click="tokenMutation.mutate()">
          {{ t('calendar.token') }}
        </button>
        <p v-if="feedUrl" class="mt-2 break-all font-mono text-xs">{{ feedUrl }}</p>
      </section>
    </template>
  </div>
</template>
