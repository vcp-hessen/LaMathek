<script setup lang="ts">
import { useMe } from '../composables/useMe'
import { queryKeys } from '../api/queryKeys'
import { useQueries, useQuery } from '@tanstack/vue-query'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  type CalendarItem,
  fetchBorrowerCalendar,
  fetchContactCalendar,
  fetchInventoryCalendar,
} from '../api/calendar'
import QueryError from '../components/QueryError.vue'
import { formatDate } from '../utils/dates'
import { fetchInventories } from '../api/inventories'
import { fetchInstallationSettings } from '../api/settings'
import ContextHelp from '../components/ContextHelp.vue'
import UiIcon from '../components/UiIcon.vue'
import CalendarLayersPanel from '../components/calendar/CalendarLayersPanel.vue'
import type { BorrowerCalendarScope, InventoryCalendarScope } from '../utils/calendarContent'
import {
  DEFAULT_BUNDESLAND,
  isoDate,
  isBundeslandCode,
  isWeekend,
  publicHolidays,
} from '../utils/germanPublicHolidays'

type CalItem = CalendarItem

type CalRole = 'borrower' | 'contact' | 'steward'

type CalDisplayItem = CalItem & { role: CalRole }

const ROLE_PRIORITY: Record<CalRole, number> = {
  borrower: 3,
  contact: 2,
  steward: 1,
}

type DayCell = {
  date: Date
  iso: string
  inMonth: boolean
  weekend: boolean
  holiday: string | null
  today: boolean
}

type Bar = {
  key: string
  loan: CalDisplayItem
  lane: number
  col: number
  span: number
  continuesBefore: boolean
  continuesAfter: boolean
}

const WEEKDAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
const BAR_ROW_HEIGHT = '1.35rem'
const MIN_BAR_ROWS = 3

const { t } = useI18n()
const mode = ref<'month' | 'table'>('month')
const cursor = ref(startOfMonth(new Date()))
const borrowerScope = ref<BorrowerCalendarScope>('borrower')
const inventoryScope = ref<Record<number, InventoryCalendarScope>>({})

const showBorrower = computed(() => borrowerScope.value === 'borrower')
const layersPanelRef = ref<HTMLDetailsElement | null>(null)

const { data: me, isLoading: meLoading } = useMe()

const { data: inventories, isLoading: inventoriesLoading } = useQuery({
  queryKey: queryKeys.inventories,
  queryFn: fetchInventories,
  enabled: () => !!me.value,
})

const calendarInventories = computed(() => inventories.value ?? [])

watch(
  calendarInventories,
  (list) => {
    const next = { ...inventoryScope.value }
    for (const inventory of list) {
      if (next[inventory.id] === undefined) {
        next[inventory.id] = inventory.canManage ? 'all' : 'contact'
      }
    }
    inventoryScope.value = next
  },
  { immediate: true },
)

const needsContactCalendar = computed(() =>
  calendarInventories.value.some((inventory) => inventoryScope.value[inventory.id] === 'contact'),
)

const inventoriesForAllLoans = computed(() =>
  calendarInventories.value.filter(
    (inventory) => inventory.canManage && inventoryScope.value[inventory.id] === 'all',
  ),
)

const borrowerQuery = useQuery({
  queryKey: ['calendar', 'borrower'],
  queryFn: fetchBorrowerCalendar,
  enabled: () => !!me.value && showBorrower.value,
})

const contactQuery = useQuery({
  queryKey: ['calendar', 'contact'],
  queryFn: fetchContactCalendar,
  enabled: () => !!me.value && needsContactCalendar.value,
})

const inventoryQueries = useQueries({
  queries: computed(() =>
    inventoriesForAllLoans.value.map((inventory) => ({
      queryKey: ['calendar', 'inventory', inventory.id] as const,
      queryFn: async () => ({
        inventoryId: inventory.id,
        items: await fetchInventoryCalendar(inventory.id),
      }),
      enabled: !!me.value,
    })),
  ),
})

const { data: installationSettings } = useQuery({
  queryKey: queryKeys.settings,
  queryFn: fetchInstallationSettings,
})

const dataLoading = computed(
  () =>
    meLoading.value ||
    (!!me.value && inventoriesLoading.value) ||
    (showBorrower.value && borrowerQuery.isLoading.value) ||
    (needsContactCalendar.value && contactQuery.isLoading.value) ||
    inventoryQueries.value.some((query) => query.isLoading),
)

// A failed layer must not look like an empty calendar.
const dataError = computed(
  () =>
    (showBorrower.value && borrowerQuery.error.value) ||
    (needsContactCalendar.value && contactQuery.error.value) ||
    inventoryQueries.value.find((query) => query.error)?.error ||
    null,
)

function retryCalendar() {
  void borrowerQuery.refetch()
  void contactQuery.refetch()
  for (const query of inventoryQueries.value) void query.refetch()
}

const totalLayerCount = computed(() => 1 + calendarInventories.value.length)

const enabledLayerCount = computed(() => {
  let count = 0
  if (showBorrower.value) count += 1
  for (const inventory of calendarInventories.value) {
    if (inventoryScope.value[inventory.id] !== 'off') count += 1
  }
  return count
})

function setInventoryScope(inventoryId: number, scope: InventoryCalendarScope) {
  inventoryScope.value = { ...inventoryScope.value, [inventoryId]: scope }
}

function closeLayersOnClickOutside(event: MouseEvent) {
  const root = layersPanelRef.value
  if (!root?.open) return
  const target = event.target
  if (target instanceof Node && root.contains(target)) return
  root.open = false
}

function closeLayersOnEscape(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  const root = layersPanelRef.value
  if (root?.open) root.open = false
}

onMounted(() => {
  document.addEventListener('click', closeLayersOnClickOutside, true)
  document.addEventListener('keydown', closeLayersOnEscape)
})

onUnmounted(() => {
  document.removeEventListener('click', closeLayersOnClickOutside, true)
  document.removeEventListener('keydown', closeLayersOnEscape)
})

function classifyRole(item: CalItem): CalRole {
  if (item.asBorrower) return 'borrower'
  if (item.asContact) return 'contact'
  return 'steward'
}

function mergeItem(map: Map<number, CalDisplayItem>, item: CalItem) {
  const role = classifyRole(item)
  const next: CalDisplayItem = { ...item, role }
  const existing = map.get(item.loanId)
  if (!existing || ROLE_PRIORITY[role] > ROLE_PRIORITY[existing.role]) {
    map.set(item.loanId, next)
  }
}

const items = computed(() => {
  const byLoan = new Map<number, CalDisplayItem>()
  if (showBorrower.value) {
    for (const item of borrowerQuery.data.value ?? []) {
      mergeItem(byLoan, item)
    }
  }
  if (needsContactCalendar.value) {
    for (const item of contactQuery.data.value ?? []) {
      if (inventoryScope.value[item.inventoryId] !== 'contact') continue
      mergeItem(byLoan, item)
    }
  }
  for (const query of inventoryQueries.value) {
    const payload = query.data
    if (!payload) continue
    for (const item of payload.items) {
      mergeItem(byLoan, item)
    }
  }
  return [...byLoan.values()].sort(
    (a, b) => a.pickupOn.localeCompare(b.pickupOn) || a.loanId - b.loanId,
  )
})

function barColorClass(role: CalRole): string {
  switch (role) {
    case 'borrower':
      return 'bg-vcp-feuergelb text-vcp-blau'
    case 'contact':
      return 'bg-vcp-blau text-white'
    case 'steward':
      return 'bg-[#5c7ea8] text-white'
  }
}

const showInventoryColumn = computed(() => calendarInventories.value.length > 1)

const monthLabel = computed(() =>
  cursor.value.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' }),
)

const calendarBundesland = computed(() => {
  const code = installationSettings.value?.calendarBundesland ?? DEFAULT_BUNDESLAND
  return isBundeslandCode(code) ? code : DEFAULT_BUNDESLAND
})

const holidays = computed(() => {
  const state = calendarBundesland.value
  const year = cursor.value.getFullYear()
  const map = publicHolidays(year, state)
  const prev = publicHolidays(year - 1, state)
  const next = publicHolidays(year + 1, state)
  for (const [key, name] of prev) map.set(key, name)
  for (const [key, name] of next) map.set(key, name)
  return map
})

const weeks = computed(() => buildWeeks(cursor.value, holidays.value))

const weekBars = computed(() => weeks.value.map((week) => barsForWeek(week, items.value)))

const monthItems = computed(() => {
  const start = isoDate(weeks.value[0]?.[0]?.date ?? cursor.value)
  const lastWeek = weeks.value[weeks.value.length - 1]
  const end = lastWeek ? lastWeek[6].iso : start
  return items.value.filter((item) => overlaps(item, start, end))
})

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

function shiftMonth(delta: number) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1)
}

function goToday() {
  cursor.value = startOfMonth(new Date())
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowLeft') shiftMonth(-1)
  if (event.key === 'ArrowRight') shiftMonth(1)
}

function buildWeeks(month: Date, holidayMap: Map<string, string>): DayCell[][] {
  const today = isoDate(new Date())
  const first = startOfMonth(month)
  const lead = (first.getDay() + 6) % 7
  const gridStart = new Date(first)
  gridStart.setDate(first.getDate() - lead)
  const weeksOut: DayCell[][] = []
  for (let w = 0; w < 6; w += 1) {
    const week: DayCell[] = []
    for (let d = 0; d < 7; d += 1) {
      const date = new Date(gridStart)
      date.setDate(gridStart.getDate() + w * 7 + d)
      const iso = isoDate(date)
      week.push({
        date,
        iso,
        inMonth: date.getMonth() === month.getMonth(),
        weekend: isWeekend(date),
        holiday: holidayMap.get(iso) ?? null,
        today: iso === today,
      })
    }
    const hasMonthDay = week.some((day) => day.inMonth)
    if (hasMonthDay) weeksOut.push(week)
  }
  return weeksOut
}

function rangeEnd(item: CalDisplayItem, visibleEnd: string): string {
  if (item.returnOn) return item.returnOn
  return visibleEnd
}

function overlaps(item: CalDisplayItem, start: string, end: string): boolean {
  const itemEnd = rangeEnd(item, end)
  return item.pickupOn <= end && itemEnd >= start
}

function barsForWeek(week: DayCell[], loans: CalDisplayItem[]): Bar[] {
  const start = week[0].iso
  const end = week[6].iso
  const active = loans
    .filter((item) => overlaps(item, start, end))
    .sort((a, b) => a.pickupOn.localeCompare(b.pickupOn) || a.loanId - b.loanId)
  const laneEnds: string[] = []
  const bars: Bar[] = []
  for (const loan of active) {
    const loanEnd = rangeEnd(loan, end)
    const visibleStart = loan.pickupOn < start ? start : loan.pickupOn
    let lane = laneEnds.findIndex((until) => until < visibleStart)
    if (lane < 0) {
      lane = laneEnds.length
      laneEnds.push(loanEnd)
    } else {
      laneEnds[lane] = loanEnd
    }
    const col = week.findIndex((day) => day.iso >= loan.pickupOn)
    const startCol = col < 0 ? 0 : col
    let last = 6
    for (let i = 6; i >= startCol; i -= 1) {
      if (week[i].iso <= loanEnd) {
        last = i
        break
      }
    }
    bars.push({
      key: `${loan.loanId}-${start}`,
      loan,
      lane,
      col: startCol,
      span: last - startCol + 1,
      continuesBefore: loan.pickupOn < start,
      continuesAfter: loan.permanent ? loanEnd >= end : (loan.returnOn ?? loan.pickupOn) > end,
    })
  }
  return bars
}

function isOffDay(day: DayCell): boolean {
  return day.weekend || day.holiday !== null
}

function weekBarRowCount(weekIndex: number): number {
  const bars = weekBars.value[weekIndex] ?? []
  const maxLane = bars.reduce((max, bar) => Math.max(max, bar.lane), -1)
  return Math.max(MIN_BAR_ROWS, maxLane + 1)
}

function weekGridTemplateRows(weekIndex: number): string {
  return `auto repeat(${weekBarRowCount(weekIndex)}, ${BAR_ROW_HEIGHT})`
}

function dayBackgroundStyle(dayIndex: number, weekIndex: number) {
  const barRows = weekBarRowCount(weekIndex)
  return {
    gridColumn: dayIndex + 1,
    gridRow: `1 / ${barRows + 2}`,
  }
}

function dayHeaderStyle(dayIndex: number) {
  return {
    gridColumn: dayIndex + 1,
    gridRow: '1',
  }
}

function barStyle(bar: Bar) {
  return {
    gridColumn: `${bar.col + 1} / span ${bar.span}`,
    gridRow: String(bar.lane + 2),
  }
}

</script>

<template>
  <div class="app-page" tabindex="0" @keydown="onKeydown">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold">
        {{ t('calendar.heading') }}
        <ContextHelp anchor="kalender" />
      </h1>
      <div class="flex flex-wrap items-center gap-2">
        <details
          v-if="me"
          ref="layersPanelRef"
          class="dropdown dropdown-end"
          @click.stop
          @keydown.stop
        >
          <summary class="btn btn-sm btn-outline gap-1.5 font-normal">
            {{ t('calendar.layersToggle') }}
            <span
              v-if="enabledLayerCount < totalLayerCount"
              class="badge badge-primary badge-sm"
            >
              {{ enabledLayerCount }}
            </span>
            <UiIcon name="chevronDown" size-class="size-3.5 shrink-0 opacity-70" />
          </summary>
          <div
            class="dropdown-content z-30 mt-1 rounded-box border border-base-200 bg-base-100 shadow-lg"
            @click.stop
          >
            <CalendarLayersPanel
              :borrower-scope="borrowerScope"
              :inventory-scope="inventoryScope"
              :inventories="calendarInventories"
              @update:borrower-scope="borrowerScope = $event"
              @update:inventory-scope="(id, scope) => setInventoryScope(id, scope)"
            />
          </div>
        </details>
        <RouterLink v-if="me" to="/calendar/feeds" class="btn btn-outline btn-sm">
          {{ t('calendar.feedsNav') }}
        </RouterLink>
        <button type="button" class="btn btn-sm" :class="mode === 'month' ? 'btn-primary' : ''" @click="mode = 'month'">
          {{ t('calendar.month') }}
        </button>
        <button type="button" class="btn btn-sm" :class="mode === 'table' ? 'btn-primary' : ''" @click="mode = 'table'">
          {{ t('calendar.table') }}
        </button>
      </div>
    </header>

    <p v-if="!me && !meLoading" class="mt-3 text-sm text-base-content/70">
      {{ t('calendar.hubSignIn') }}
      <a class="link" href="/login">{{ t('auth.signIn') }}</a>
    </p>

    <div class="mt-4 flex flex-wrap items-center justify-between gap-2">
      <div class="flex items-center gap-1">
        <button
          type="button"
          class="btn btn-ghost btn-sm btn-square"
          :aria-label="t('calendar.prev')"
          @click="shiftMonth(-1)"
        >
          <UiIcon name="chevronLeft" size-class="size-4" />
        </button>
        <button type="button" class="btn btn-ghost btn-sm" @click="goToday">
          {{ t('calendar.today') }}
        </button>
        <button
          type="button"
          class="btn btn-ghost btn-sm btn-square"
          :aria-label="t('calendar.next')"
          @click="shiftMonth(1)"
        >
          <UiIcon name="chevronRight" size-class="size-4" />
        </button>
      </div>
      <p class="text-lg font-medium capitalize">{{ monthLabel }}</p>
    </div>

    <p v-if="me && dataLoading" class="mt-4 text-sm">{{ t('auth.loading') }}</p>
    <QueryError v-else-if="me && dataError" class="mt-4" :error="dataError" @retry="retryCalendar()" />

    <template v-else-if="me">
      <div v-if="mode === 'month'" class="mt-3 overflow-x-auto">
        <div class="grid min-w-[40rem] grid-cols-7 text-xs text-base-content/60">
          <div v-for="name in WEEKDAYS" :key="name" class="px-1 py-1">{{ name }}</div>
        </div>
        <section
          v-for="(week, weekIndex) in weeks"
          :key="week[0].iso"
          class="grid min-w-[40rem] grid-cols-7 gap-y-0.5 border-t border-base-300 px-0.5 pb-1"
          :style="{ gridTemplateRows: weekGridTemplateRows(weekIndex) }"
        >
          <div
            v-for="(day, dayIndex) in week"
            :key="`bg-${day.iso}`"
            class="z-0"
            :class="isOffDay(day) ? 'bg-base-200/80' : ''"
            :style="dayBackgroundStyle(dayIndex, weekIndex)"
          />
          <div
            v-for="(day, dayIndex) in week"
            :key="day.iso"
            class="relative z-10 min-h-8 px-1 py-0.5 text-xs"
            :class="day.inMonth ? '' : 'text-base-content/30'"
            :style="dayHeaderStyle(dayIndex)"
          >
            <span
              class="inline-flex size-5 items-center justify-center rounded-full"
              :class="day.today ? 'bg-vcp-blau text-white' : ''"
              :title="day.holiday ?? ''"
            >
              {{ day.date.getDate() }}
            </span>
            <span v-if="day.holiday && day.inMonth" class="ml-1 text-[10px] text-base-content/60">
              {{ day.holiday }}
            </span>
          </div>
          <RouterLink
            v-for="bar in weekBars[weekIndex]"
            :key="bar.key"
            :to="`/inventories/${bar.loan.inventoryId}/loans/${bar.loan.loanId}`"
            class="relative z-10 mx-0.5 truncate px-1 text-[11px] leading-5"
            :class="[
              barColorClass(bar.loan.role),
              bar.continuesBefore ? 'rounded-l-none' : 'rounded-l',
              bar.continuesAfter ? 'rounded-r-none' : 'rounded-r',
            ]"
            :style="barStyle(bar)"
            :title="`${bar.loan.title} · ${bar.loan.inventoryName}`"
          >
            {{ bar.loan.title }}<span v-if="bar.loan.permanent"> · {{ t('loans.kindPermanent') }}</span>
          </RouterLink>
        </section>
      </div>

      <table v-else class="mt-4 w-full text-sm">
        <thead>
          <tr class="text-left">
            <th v-if="showInventoryColumn">{{ t('loans.columnInventory') }}</th>
            <th>{{ t('calendar.colTitle') }}</th>
            <th>{{ t('calendar.colFrom') }}</th>
            <th>{{ t('calendar.colTo') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in monthItems" :key="item.loanId">
            <td v-if="showInventoryColumn">{{ item.inventoryName }}</td>
            <td>
              <RouterLink :to="`/inventories/${item.inventoryId}/loans/${item.loanId}`">
                {{ item.title }}
              </RouterLink>
              <span v-if="item.permanent" class="ml-2 text-xs opacity-70">{{ t('loans.kindPermanent') }}</span>
            </td>
            <td>{{ formatDate(item.pickupOn) }}</td>
            <td>{{ formatDate(item.returnOn) }}</td>
          </tr>
          <tr v-if="monthItems.length === 0">
            <td :colspan="showInventoryColumn ? 4 : 3" class="py-3 text-base-content/60">
              {{ t('calendar.emptyMonth') }}
            </td>
          </tr>
        </tbody>
      </table>

      <p class="mt-4 flex flex-wrap gap-3 text-xs text-base-content/70">
        <span><span class="mr-1 inline-block size-2 rounded-sm bg-vcp-feuergelb" />{{ t('calendar.contentBorrower') }}</span>
        <span><span class="mr-1 inline-block size-2 rounded-sm bg-vcp-blau" />{{ t('calendar.contentContact') }}</span>
        <span><span class="mr-1 inline-block size-2 rounded-sm bg-[#5c7ea8]" />{{ t('calendar.contentAllLoans') }}</span>
      </p>

    </template>
  </div>
</template>
