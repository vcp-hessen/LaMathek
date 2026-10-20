<script setup lang="ts">
import { formatDate, formatDateTime } from '../../utils/dates'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { JournalEntry } from '../../schemas/journal'

const props = defineProps<{
  entries: JournalEntry[] | undefined
  loading?: boolean
  title: string
}>()

const { t, te, tm, rt } = useI18n()

type JournalRow = JournalEntry & { items: string[] }

/**
 * Consecutive entries of the same kind by the same person in the same minute
 * (e.g. every Position of a Set being requested) collapse into one row.
 */
const rows = computed<JournalRow[]>(() => {
  const result: JournalRow[] = []
  for (const entry of props.entries ?? []) {
    const item = typeof entry.payload.item === 'string' ? entry.payload.item : ''
    const prev = result[result.length - 1]
    if (
      prev &&
      item &&
      prev.items.length &&
      prev.kind === entry.kind &&
      prev.actor?.id === entry.actor?.id &&
      (prev.createdAt ?? '').slice(0, 16) === (entry.createdAt ?? '').slice(0, 16) &&
      !entry.payload.reason
    ) {
      prev.items.push(item)
      continue
    }
    result.push({ ...entry, items: item ? [item] : [] })
  }
  return result
})

function actorLabel(entry: JournalEntry): string {
  const actor = entry.actor
  if (!actor) return t('journal.systemActor')
  const name = (actor.name || actor.email || `#${actor.id}`).trim()
  const real = entry.realActor
  if (!real) return name
  return t('journal.impersonatedBy', { name, realName: (real.name || `#${real.id}`).trim() })
}

// Kinds contain dots ("line.request"), so they cannot be addressed as key paths.
const kindMessages = computed(() => tm('journal.kind') as Record<string, unknown>)

function kindLabel(kind: string): string {
  const message = kindMessages.value[kind]
  return message ? rt(message as Parameters<typeof rt>[0]) : kind
}

function fieldLabel(field: string): string {
  const key = `journal.field.${field}`
  return te(key) ? t(key) : field
}

function show(value: unknown): string {
  if (value === null || value === undefined || value === '') return t('journal.empty_value')
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return formatDate(value)
  }
  return String(value)
}

/** One line under the event: what it was about and why. */
function payloadSummary(entry: JournalRow): string {
  const p = entry.payload as Record<string, unknown>
  const parts: string[] = []
  if (entry.items.length) parts.push(entry.items.join(', '))
  if (typeof p.set === 'string' && p.set) parts.push(p.set)
  if (p.changes && typeof p.changes === 'object') {
    for (const [field, change] of Object.entries(p.changes as Record<string, { from: unknown; to: unknown }>)) {
      parts.push(
        t('journal.fromTo', { field: fieldLabel(field), from: show(change.from), to: show(change.to) }),
      )
    }
  }
  if (typeof p.fromQuantity === 'number' && typeof p.toQuantity === 'number') {
    parts.push(t('journal.quantityChange', { from: p.fromQuantity, to: p.toQuantity }))
  }
  if (typeof p.audience === 'string') parts.push(t(`journal.audience.${p.audience}`))
  if (typeof p.pdfKind === 'string' && p.pdfKind) parts.push(t(`journal.pdfKind.${p.pdfKind}`))
  if (typeof p.reason === 'string' && p.reason) {
    const key = `journal.skipReason.${p.reason}`
    parts.push(te(key) ? t(key) : p.reason)
  }
  if (typeof p.error === 'string' && p.error) parts.push(p.error)
  return parts.join(' · ')
}

const when = formatDateTime
</script>

<template>
  <section class="space-y-3">
    <h2 class="text-lg font-semibold">{{ title }}</h2>
    <p v-if="loading" class="text-sm text-base-content/60">{{ t('auth.loading') }}</p>
    <p v-else-if="!rows.length" class="text-sm text-base-content/60">{{ t('journal.empty') }}</p>
    <ul v-else class="divide-y divide-base-300/60 rounded-lg border border-base-300/60">
      <li v-for="entry in rows" :key="entry.id" class="px-3 py-2.5 text-sm">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <span class="font-medium">{{ kindLabel(entry.kind) }}</span>
          <time class="text-xs text-base-content/60" :datetime="entry.createdAt ?? undefined">
            {{ when(entry.createdAt) }}
          </time>
        </div>
        <p v-if="payloadSummary(entry)" class="mt-0.5 text-base-content/80">
          {{ payloadSummary(entry) }}
        </p>
        <p class="mt-0.5 text-xs text-base-content/60">{{ actorLabel(entry) }}</p>
      </li>
    </ul>
  </section>
</template>
