<script setup lang="ts">
import type { Category } from '../schemas/material'
import NamedOptionCombobox from './NamedOptionCombobox.vue'

defineProps<{
  categories: Category[]
}>()

const categoryText = defineModel<string>({ required: true })
</script>

<template>
  <NamedOptionCombobox
    v-model="categoryText"
    :options="categories"
    :placeholder="$t('material.categoryPlaceholder')"
    clear-label-key="material.categoryNone"
    empty-label-key="material.categoryEmpty"
    menu-label-key="material.categoryMenu"
    new-label-key="material.categoryNew"
  />
</template>
