<script setup lang="ts">
import QueryError from './QueryError.vue'
import { queryKeys } from '../api/queryKeys'
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchAuditEvents } from '../api/audit'
import type { AuditEvent } from '../schemas/audit'
import { userLabel } from '../utils/userLabel'

const { t, locale } = useI18n()

const { data: events, isLoading, isError, error: loadError, refetch: retryLoad } = useQuery({
  queryKey: queryKeys.auditEvents,
  queryFn: fetchAuditEvents,
})

const formatter = computed(
  () =>
    new Intl.DateTimeFormat(locale.value, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }),
)

function formatWhen(iso: string | null): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return formatter.value.format(date)
}

function actionLabel(action: string): string {
  const key = `audit.actions.${action}`
  const translated = t(key)
  return translated === key ? action : translated
}

function detailSummary(event: AuditEvent): string {
  if (event.action === 'installation_settings_updated' && event.detail?.changes) {
    const changes = event.detail.changes as Record<string, { old?: unknown; new?: unknown }>
    const fields = Object.keys(changes)
    if (fields.length === 0) return ''
    return t('audit.settingsFieldsChanged', { fields: fields.join(', ') })
  }
  return ''
}
</script>

<template>
  <section class="space-y-3">
    <h2 class="text-lg font-semibold">{{ t('audit.heading') }}</h2>
    <p v-if="isLoading" class="text-sm opacity-70">{{ t('auth.loading') }}</p>
    <QueryError v-else-if="isError" :error="loadError" @retry="retryLoad()" />
    <p v-else-if="!(events?.length)" class="text-sm opacity-70">{{ t('audit.empty') }}</p>
    <div v-else class="overflow-x-auto rounded-lg border border-base-200">
      <table class="table table-sm">
        <thead>
          <tr>
            <th>{{ t('audit.columnWhen') }}</th>
            <th>{{ t('audit.columnAction') }}</th>
            <th>{{ t('audit.columnActor') }}</th>
            <th>{{ t('audit.columnTarget') }}</th>
            <th>{{ t('audit.columnReason') }}</th>
            <th>{{ t('audit.columnDetail') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="event in events" :key="event.id">
            <td class="whitespace-nowrap text-xs">{{ formatWhen(event.createdAt) }}</td>
            <td class="text-sm">{{ actionLabel(event.action) }}</td>
            <td class="text-sm">{{ event.actor ? userLabel(event.actor) : '—' }}</td>
            <td class="text-sm">
              {{ event.targetUser ? userLabel(event.targetUser) : '—' }}
            </td>
            <td class="max-w-xs text-sm">{{ event.reason || '—' }}</td>
            <td class="max-w-md text-xs opacity-80">{{ detailSummary(event) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
