<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { websiteHref } from '../composables/useWebsiteHref'
import type { InstallationSettings } from '../schemas/settings'
import { useUiStore } from '../stores/ui'
import UiIcon from './UiIcon.vue'

const props = defineProps<{
  settings?: InstallationSettings | null
}>()

const { t } = useI18n()
const ui = useUiStore()

const themeActionLabel = computed(() =>
  ui.theme === 'light' ? t('theme.dark') : t('theme.light'),
)

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
      <a
        v-if="siteUrl"
        :href="siteUrl"
        class="link link-hover font-medium"
        target="_blank"
        rel="noopener noreferrer"
      >
        {{ provider || props.settings?.website }}
      </a>
      <span v-else-if="provider" class="font-medium">{{ provider }}</span>
      <RouterLink to="/impressum" class="link link-hover">
        {{ t('impressum.nav') }}
      </RouterLink>
      <RouterLink to="/datenschutz" class="link link-hover">
        {{ t('privacy.nav') }}
      </RouterLink>
      <RouterLink to="/calendar" class="link link-hover">
        {{ t('nav.calendar') }}
      </RouterLink>
      <RouterLink to="/hilfe" class="link link-hover">
        {{ t('help.nav') }}
      </RouterLink>
      <button
        type="button"
        class="link link-hover inline-flex items-center gap-1 border-0 bg-transparent p-0 font-inherit text-inherit"
        :aria-label="themeActionLabel"
        :title="themeActionLabel"
        @click="ui.toggleTheme()"
      >
        <UiIcon :name="ui.theme === 'light' ? 'moon' : 'sun'" size-class="size-3.5" />
      </button>
    </div>
  </footer>
</template>
