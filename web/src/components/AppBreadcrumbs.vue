<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppBreadcrumbs } from '../composables/useAppBreadcrumbs'

const { t } = useI18n()
const { items } = useAppBreadcrumbs()
</script>

<template>
  <nav v-if="items.length" class="min-w-0" :aria-label="t('shell.breadcrumbs')">
    <div class="breadcrumbs text-sm">
      <ul>
        <li v-for="(crumb, index) in items" :key="index">
          <RouterLink v-if="crumb.to" :to="crumb.to" class="truncate max-w-[12rem] sm:max-w-none">
            {{ crumb.label }}
          </RouterLink>
          <span v-else class="truncate font-semibold max-w-[14rem] sm:max-w-none">{{ crumb.label }}</span>
        </li>
      </ul>
    </div>
  </nav>
</template>
