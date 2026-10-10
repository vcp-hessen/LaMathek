<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchInstallationSettings } from '../api/settings'
import { websiteHref } from '../composables/useWebsiteHref'

const { t } = useI18n()
const { data: settings, isLoading } = useQuery({
  queryKey: ['settings'],
  queryFn: fetchInstallationSettings,
})

const siteUrl = computed(() => websiteHref(settings.value?.website))

const textEntries = computed(() => {
  if (!settings.value) return []
  const s = settings.value
  return [
    { label: t('settings.legalNameLabel'), value: s.legalName },
    { label: t('settings.legalAddressLabel'), value: s.legalAddress },
    { label: t('settings.emailLabel'), value: s.email },
    { label: t('settings.phoneLabel'), value: s.phone },
    { label: t('settings.representedByLabel'), value: s.representedBy },
    { label: t('settings.registerLabel'), value: s.register },
    { label: t('settings.contentResponsibleLabel'), value: s.contentResponsible },
  ].filter((row) => row.value.trim())
})

const hasContent = computed(() => textEntries.value.length > 0 || siteUrl.value)
</script>

<template>
  <div class="app-page space-y-4">
    <h1 class="text-2xl font-bold">{{ t('impressum.heading') }}</h1>
    <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
    <dl v-else class="space-y-4">
      <div v-for="row in textEntries" :key="row.label">
        <dt class="text-sm font-medium opacity-80">{{ row.label }}</dt>
        <dd class="mt-1 whitespace-pre-wrap">{{ row.value }}</dd>
      </div>
      <div v-if="siteUrl">
        <dt class="text-sm font-medium opacity-80">{{ t('settings.websiteLabel') }}</dt>
        <dd class="mt-1">
          <a :href="siteUrl" class="link" target="_blank" rel="noopener noreferrer">
            {{ settings?.website }}
          </a>
        </dd>
      </div>
      <p v-if="!hasContent" class="text-sm opacity-70">{{ t('impressum.empty') }}</p>
    </dl>
  </div>
</template>
