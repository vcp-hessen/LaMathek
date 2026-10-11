<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { websiteHref } from '../composables/useWebsiteHref'
import type { InstallationSettings } from '../schemas/settings'

const props = defineProps<{
  settings?: InstallationSettings | null
}>()

const { t } = useI18n()

const provider = computed(
  () => props.settings?.legalName?.trim() || props.settings?.title?.trim() || '',
)

const siteUrl = computed(() => websiteHref(props.settings?.website))
</script>

<template>
  <footer class="shrink-0 border-t border-base-300/50 bg-base-100">
    <div
      class="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 px-4 py-2.5 text-center text-xs text-base-content/80"
    >
      <span v-if="provider" class="font-medium">{{ provider }}</span>
      <RouterLink to="/impressum" class="link link-hover">
        {{ t('impressum.nav') }}
      </RouterLink>
      <a
        v-if="siteUrl"
        :href="siteUrl"
        class="link link-hover"
        target="_blank"
        rel="noopener noreferrer"
      >
        {{ t('footer.website') }}
      </a>
    </div>
  </footer>
</template>
