<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import UiIcon from './UiIcon.vue'

const props = defineProps<{
  anchor: string
  label?: string
}>()

const { t, te } = useI18n()
const open = ref(false)

const text = () => {
  const key = `help.context.${props.anchor}`
  return te(key) ? t(key) : t(`help.glossary.${props.anchor}.body`)
}
</script>

<template>
  <span class="relative inline-flex">
    <button
      type="button"
      class="inline-flex items-center text-base-content/50 hover:text-vcp-blau"
      :aria-expanded="open"
      :aria-label="label ?? t('help.glossaryLink')"
      @click="open = !open"
    >
      <UiIcon name="info" size-class="size-4" />
    </button>
    <div
      v-if="open"
      class="absolute left-0 top-6 z-20 w-72 rounded-md border border-base-300 bg-base-100 p-3 text-sm shadow"
      role="dialog"
    >
      <p>{{ text() }}</p>
      <RouterLink class="mt-2 inline-block text-vcp-blau" :to="`/hilfe#${anchor}`" @click="open = false">
        {{ t('help.glossaryLink') }}
      </RouterLink>
    </div>
  </span>
</template>
