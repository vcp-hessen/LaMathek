<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t, tm } = useI18n()

const entryKeys = [
  'verleih',
  'position',
  'ausleihende',
  'ansprechperson',
  'materialart',
  'variante',
  'einzelteil',
  'menge',
  'set',
  'zuordnung',
  'optional',
  'dauerleihgabe',
  'verlust',
  'verbrauch',
  'schaden',
  'materialwart',
  'inventar',
  'leserecht',
  'uebernahme',
  'rueckgabe',
  'kalender',
  'dashboard',
] as const

const entries = computed(() =>
  entryKeys.map((key) => ({
    id: key,
    title: t(`help.glossary.${key}.title`),
    body: t(`help.glossary.${key}.body`),
  })),
)

const hasEntries = computed(() => {
  const raw = tm('help.glossary')
  return raw != null && typeof raw === 'object'
})
</script>

<template>
  <div class="app-page mx-auto max-w-3xl space-y-6">
    <header>
      <h1 class="text-2xl font-semibold text-vcp-blau">{{ t('help.glossaryPageTitle') }}</h1>
      <p class="mt-2 text-base-content/80">{{ t('help.glossaryIntro') }}</p>
    </header>
    <section v-if="hasEntries" class="space-y-8">
      <article
        v-for="entry in entries"
        :id="entry.id"
        :key="entry.id"
        class="scroll-mt-24 border-b border-base-300/60 pb-6 last:border-0"
      >
        <h2 class="text-lg font-semibold text-vcp-blau">{{ entry.title }}</h2>
        <p class="mt-2 leading-relaxed text-base-content/90">{{ entry.body }}</p>
      </article>
    </section>
  </div>
</template>
