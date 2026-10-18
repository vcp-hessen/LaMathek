<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { JournalEntry } from '../../schemas/journal'

const props = defineProps<{
  entries: JournalEntry[] | undefined
  loading?: boolean
  title: string
}>()

const { t } = useI18n()

const sorted = computed(() => props.entries ?? [])

function actorLabel(entry: JournalEntry): string {
  const actor = entry.actor
  if (!actor) return t('journal.systemActor')
  return (actor.name || actor.email || `#${actor.id}`).trim()
}

function kindLabel(kind: string): string {
  const key = `journal.kind.${kind}`
  const translated = t(key)
  return translated === key ? kind : translated
}

function payloadSummary(entry: JournalEntry): string {
  const payload = entry.payload
  if (payload.fields && Array.isArray(payload.fields)) {
    return payload.fields.join(', ')
  }
  if (typeof payload.reason === 'string' && payload.reason) return payload.reason
  if (typeof payload.status === 'string' && payload.status) return payload.status
  if (typeof payload.pdfKind === 'string' && payload.pdfKind) {
    return t(`journal.pdfKind.${payload.pdfKind}`)
  }
  return ''
}
</script>

<template>
  <section class="space-y-3">
    <h2 class="text-lg font-semibold">{{ title }}</h2>
    <p v-if="loading" class="text-sm text-base-content/60">{{ t('app.loading') }}</p>
    <p v-else-if="!sorted.length" class="text-sm text-base-content/60">{{ t('journal.empty') }}</p>
    <ul v-else class="divide-y divide-base-300/60 rounded-lg border border-base-300/60">
      <li v-for="entry in sorted" :key="entry.id" class="px-3 py-2.5 text-sm">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <span class="font-medium">{{ kindLabel(entry.kind) }}</span>
          <time class="text-xs text-base-content/60">{{ entry.createdAt }}</time>
        </div>
        <p v-if="payloadSummary(entry)" class="mt-0.5 text-base-content/80">
          {{ payloadSummary(entry) }}
        </p>
        <p class="mt-0.5 text-xs text-base-content/60">{{ actorLabel(entry) }}</p>
      </li>
    </ul>
  </section>
</template>
