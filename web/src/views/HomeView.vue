<script setup lang="ts">
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, watchEffect } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchAuthMode } from '../api/authMode'
import { fetchInstallationSettings } from '../api/settings'
import { fetchMe, logout } from '../api/me'
import InstallationSettingsForm from '../components/InstallationSettingsForm.vue'
import SuperuserList from '../components/SuperuserList.vue'

const { t } = useI18n()
const queryClient = useQueryClient()

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

const displayName = computed(
  () => me.value?.name ?? me.value?.email ?? me.value?.sub ?? '',
)

const title = computed(() => settings.value?.title ?? t('app.productName'))
const subtitle = computed(() => settings.value?.subtitle ?? '')

watchEffect(() => {
  if (settings.value?.title) {
    document.title = settings.value.title
  }
})

async function onSignOut() {
  await logout()
  await queryClient.invalidateQueries({ queryKey: ['me'] })
}
</script>

<template>
  <div class="min-h-screen bg-base-200">
    <div class="navbar bg-base-100 shadow-sm">
      <div class="flex-1 flex-col items-start px-2 py-1">
        <span class="text-xl font-semibold">{{ title }}</span>
        <span v-if="subtitle" class="text-xs text-base-content/60">{{ subtitle }}</span>
      </div>
      <div class="flex-none gap-2 pr-2">
        <a v-if="!me && !meLoading" class="btn btn-primary" href="/login">
          {{ t('auth.signIn') }}
        </a>
        <button
          v-else-if="me"
          type="button"
          class="btn btn-ghost"
          @click="onSignOut"
        >
          {{ t('auth.signOut') }}
        </button>
      </div>
    </div>

    <main class="hero min-h-[70vh]">
      <div class="hero-content flex-col gap-8">
        <div class="max-w-md text-center">
          <h1 class="text-4xl font-bold">{{ title }}</h1>
          <p v-if="subtitle" class="py-4 text-base-content/70">{{ subtitle }}</p>
          <p v-if="settingsLoading || meLoading" class="text-sm">
            {{ t('auth.loading') }}
          </p>
          <p v-else-if="me" class="text-lg">
            {{ t('auth.signedInAs', { name: displayName }) }}
          </p>
          <a v-else class="btn btn-primary" href="/login">{{ t('auth.signIn') }}</a>
          <p v-if="authMode?.devBypass" class="mt-4 text-xs text-warning">
            {{ t('dev.authBypass') }}
          </p>
          <p class="mt-6 text-xs text-base-content/50">{{ t('app.productName') }}</p>
        </div>

        <div v-if="me?.isSuperuser && settings" class="w-full max-w-lg space-y-6">
          <InstallationSettingsForm :settings="settings" />
          <SuperuserList />
        </div>
      </div>
    </main>
  </div>
</template>
