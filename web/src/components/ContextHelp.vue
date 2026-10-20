<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import UiIcon from './UiIcon.vue'

/** Info button with a short explanation and, if there is one, a link to the glossary entry. */
const props = defineProps<{
  anchor: string
  label?: string
}>()

const { t, te } = useI18n()
const open = ref(false)
const root = ref<HTMLElement | null>(null)
const panelId = `context-help-${Math.random().toString(36).slice(2)}`

const text = () => {
  const key = `help.context.${props.anchor}`
  return te(key) ? t(key) : t(`help.glossary.${props.anchor}.body`)
}
const hasGlossaryEntry = () => te(`help.glossary.${props.anchor}.title`)

function onDocumentClick(event: MouseEvent) {
  if (root.value && !root.value.contains(event.target as Node)) open.value = false
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') open.value = false
}

watch(open, (isOpen) => {
  if (isOpen) {
    document.addEventListener('click', onDocumentClick, true)
    document.addEventListener('keydown', onKeydown)
  } else {
    document.removeEventListener('click', onDocumentClick, true)
    document.removeEventListener('keydown', onKeydown)
  }
})

onBeforeUnmount(() => {
  open.value = false
})
</script>

<template>
  <span ref="root" class="relative inline-flex align-middle">
    <button
      type="button"
      class="inline-flex items-center text-base-content/50 hover:text-vcp-blau"
      :aria-expanded="open"
      :aria-controls="panelId"
      :aria-label="label ?? t('help.glossaryLink')"
      @click="open = !open"
    >
      <UiIcon name="info" size-class="size-4" />
    </button>
    <div
      v-if="open"
      :id="panelId"
      class="absolute left-0 top-6 z-20 w-72 max-w-[calc(100vw-2rem)] rounded-md border border-base-300 bg-base-100 p-3 text-left text-sm font-normal shadow"
      role="note"
    >
      <p>{{ text() }}</p>
      <RouterLink
        v-if="hasGlossaryEntry()"
        class="mt-2 inline-block text-vcp-blau"
        :to="`/hilfe#${anchor}`"
        @click="open = false"
      >
        {{ t('help.glossaryLink') }}
      </RouterLink>
    </div>
  </span>
</template>
