<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<template>
  <div class="app-page space-y-3">
    <h1 class="text-2xl font-bold">{{ t('app.notFoundTitle') }}</h1>
    <p class="text-base-content/80">{{ t('app.notFound') }}</p>
    <RouterLink to="/" class="link">{{ t('app.backHome') }}</RouterLink>
  </div>
</template>
