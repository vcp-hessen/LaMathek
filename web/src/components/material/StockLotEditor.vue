<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'
import PhotoGallery from '../PhotoGallery.vue'
import VariantAxisSelects from '../VariantAxisSelects.vue'
import type { StockLotListItem } from './materialTableSetup'

const props = defineProps<{
  inventoryId: number
  lot: StockLotListItem
  draft: { label: string; variant: Record<string, string>; quantity: number }
  formError: string | null
  dirty: boolean
  saving: boolean
  deleting: boolean
  stocksQueryKey: unknown[]
}>()

const emit = defineEmits<{
  save: []
  delete: []
}>()

const { t } = useI18n()
const queryClient = useQueryClient()
</script>

<template>
  <form class="space-y-3 p-3 sm:p-4" @submit.prevent="emit('save')">
    <p class="text-sm">
      <span class="text-xs opacity-80">{{ t('material.filterMaterialType') }}: </span>
      {{ lot.materialTypeName }}
    </p>
    <label class="flex min-w-0 flex-col gap-1">
      <span class="text-xs opacity-80">{{ t('material.stockLotLabel') }}</span>
      <input
        v-model="draft.label"
        type="text"
        class="input input-bordered w-full"
        :placeholder="t('material.stockLotLabelPlaceholder')"
      />
    </label>
    <VariantAxisSelects
      v-if="lot.variants.length"
      v-model="draft.variant"
      :axes="lot.variants"
      optional
    />
    <label class="flex min-w-0 flex-col gap-1">
      <span class="text-xs opacity-80">{{ t('material.stockQuantity') }}</span>
      <input
        v-model.number="draft.quantity"
        type="number"
        min="0"
        step="1"
        class="input input-bordered w-full"
        required
      />
    </label>
    <div>
      <h3 class="mb-2 text-sm font-semibold">{{ t('photos.heading') }}</h3>
      <PhotoGallery
        :owner="{
          kind: 'stockLot',
          inventoryId: props.inventoryId,
          lotId: lot.id,
        }"
        :photos="lot.photos ?? []"
        @change="() => queryClient.invalidateQueries({ queryKey: stocksQueryKey })"
      />
    </div>
    <p v-if="formError" class="text-sm text-error">{{ formError }}</p>
    <div class="flex flex-wrap justify-end gap-2">
      <button
        type="button"
        class="btn btn-ghost btn-sm"
        :disabled="deleting"
        @click="emit('delete')"
      >
        {{ t('material.stockLotRemove') }}
      </button>
      <button type="submit" class="btn btn-primary btn-sm" :disabled="saving || !dirty">
        {{ t('material.save') }}
      </button>
    </div>
  </form>
</template>
