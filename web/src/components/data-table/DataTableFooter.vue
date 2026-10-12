<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { DATA_TABLE_PAGE_SIZE_OPTIONS } from './pageSize'

defineProps<{
  pageFrom: number
  pageTo: number
  total: number
  currentPage: number
  pageCount: number
  pageSize: number
}>()

const emit = defineEmits<{
  'update:pageSize': [size: number]
  goToPage: [page: number]
}>()

const { t } = useI18n()
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-3 border-t border-base-200 px-3 py-2.5">
    <p class="text-xs opacity-70">
      {{ t('dataTable.pageRange', { from: pageFrom, to: pageTo, total }) }}
      <span class="opacity-80">
        ·
        {{ t('dataTable.pageOf', { current: currentPage, pages: pageCount }) }}
      </span>
    </p>
    <div class="flex flex-wrap items-center gap-2">
      <label class="flex items-center gap-2">
        <span class="text-xs opacity-80">{{ t('dataTable.pageSize') }}</span>
        <select
          :value="pageSize"
          class="select select-bordered select-sm w-20"
          @change="emit('update:pageSize', Number(($event.target as HTMLSelectElement).value))"
        >
          <option v-for="size in DATA_TABLE_PAGE_SIZE_OPTIONS" :key="size" :value="size">
            {{ size }}
          </option>
        </select>
      </label>
      <div class="join">
        <button
          type="button"
          class="btn btn-sm join-item"
          :disabled="currentPage <= 1"
          :aria-label="t('dataTable.previousPage')"
          @click="emit('goToPage', currentPage - 1)"
        >
          ‹
        </button>
        <button
          type="button"
          class="btn btn-sm join-item"
          :disabled="currentPage >= pageCount"
          :aria-label="t('dataTable.nextPage')"
          @click="emit('goToPage', currentPage + 1)"
        >
          ›
        </button>
      </div>
    </div>
  </div>
</template>
