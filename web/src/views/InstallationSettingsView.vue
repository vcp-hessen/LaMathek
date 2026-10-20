<script setup lang="ts">
import { useMe } from '../composables/useMe'
import { queryKeys } from '../api/queryKeys'
import { useQuery } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'
import { fetchInstallationSettings } from '../api/settings'
import InstallationSettingsForm from '../components/InstallationSettingsForm.vue'

const { t } = useI18n()

const { data: settings, isLoading: settingsLoading } = useQuery({
  queryKey: queryKeys.settings,
  queryFn: fetchInstallationSettings,
})

const { data: me, isLoading: meLoading } = useMe()
</script>

<template>
  <div class="app-page space-y-4">
    <h1 class="text-2xl font-bold">{{ t('settings.heading') }}</h1>
    <p v-if="settingsLoading || meLoading" class="text-sm">{{ t('auth.loading') }}</p>
    <p v-else-if="!me?.isSuperuser" class="text-sm text-base-content/70">
      {{ t('settings.superuserOnly') }}
    </p>
    <InstallationSettingsForm v-else-if="settings" :settings="settings" />
  </div>
</template>
