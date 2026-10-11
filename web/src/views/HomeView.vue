<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, watchEffect } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchAuthMode } from '../api/authMode'
import { fetchInstallationSettings } from '../api/settings'
import { fetchMe } from '../api/me'
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

</script>

<template>
  <div class="hero min-h-0 flex-1">
      <div class="hero-content flex-col gap-8">
        <div class="max-w-md text-center">
          <img
            src="/logo.svg"
            width="80"
            height="80"
            alt=""
            class="mx-auto mb-4 size-20 rounded-2xl shadow-md"
          />
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

      </div>
  </div>
</template>
