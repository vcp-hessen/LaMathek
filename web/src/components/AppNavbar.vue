<script setup lang="ts">
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchInstallationSettings } from '../api/settings'
import { fetchMe, logout } from '../api/me'

const { t } = useI18n()
const queryClient = useQueryClient()

const { data: settings } = useQuery({
  queryKey: ['settings'],
  queryFn: fetchInstallationSettings,
})

const { data: me } = useQuery({
  queryKey: ['me'],
  queryFn: fetchMe,
})

const title = computed(() => settings.value?.title ?? t('app.productName'))

async function onSignOut() {
  await logout()
  await queryClient.invalidateQueries({ queryKey: ['me'] })
}
</script>

<template>
  <div class="navbar bg-base-100 shadow-sm">
    <div class="flex-1 gap-4 px-2">
      <RouterLink to="/" class="text-xl font-semibold">{{ title }}</RouterLink>
      <RouterLink
        v-if="me"
        to="/inventories"
        class="link link-hover text-sm"
      >
        {{ t('inventories.nav') }}
      </RouterLink>
    </div>
    <div class="flex-none gap-2 pr-2">
      <a v-if="!me" class="btn btn-primary btn-sm" href="/login">
        {{ t('auth.signIn') }}
      </a>
      <button v-else type="button" class="btn btn-ghost btn-sm" @click="onSignOut">
        {{ t('auth.signOut') }}
      </button>
    </div>
  </div>
</template>
