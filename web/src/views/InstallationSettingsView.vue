<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'
import { fetchInstallationSettings } from '../api/settings'
import { fetchMe } from '../api/me'
import InstallationSettingsForm from '../components/InstallationSettingsForm.vue'
import SuperuserList from '../components/SuperuserList.vue'

const { t } = useI18n()

const { data: settings, isLoading: settingsLoading } = useQuery({
  queryKey: ['settings'],
  queryFn: fetchInstallationSettings,
})

const { data: me, isLoading: meLoading } = useQuery({
  queryKey: ['me'],
  queryFn: fetchMe,
})
</script>

<template>
  <div class="app-page space-y-6">
    <h1 class="text-2xl font-bold">{{ t('settings.heading') }}</h1>
    <p v-if="settingsLoading || meLoading" class="text-sm">{{ t('auth.loading') }}</p>
    <p v-else-if="!me?.isSuperuser" class="text-sm text-base-content/70">
      {{ t('settings.superuserOnly') }}
    </p>
    <template v-else-if="settings">
      <InstallationSettingsForm :settings="settings" />
      <SuperuserList />
    </template>
  </div>
</template>
