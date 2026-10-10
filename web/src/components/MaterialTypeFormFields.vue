<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { Category, VariantAxis } from '../schemas/material'
import MaterialTypeVariantsEditor from './MaterialTypeVariantsEditor.vue'

defineProps<{
  categories: Category[]
}>()

const name = defineModel<string>('name', { required: true })
const tracking = defineModel<'piece' | 'stock'>('tracking', { required: true })
const shortName = defineModel<string>('shortName', { required: true })
const description = defineModel<string>('description', { required: true })
const unit = defineModel<string>('unit', { required: true })
const consumable = defineModel<boolean>('consumable', { required: true })
const variants = defineModel<VariantAxis[]>('variants', { required: true })
const categoryText = defineModel<string>('categoryText', { required: true })

const { t } = useI18n()

function setTrackingFromToggle(isStock: boolean) {
  tracking.value = isStock ? 'stock' : 'piece'
}
</script>

<template>
  <div class="material-type-form flex flex-col gap-4">
  <div class="grid grid-cols-1 gap-3 min-[40rem]:grid-cols-4">
    <label class="flex min-w-0 flex-col gap-1 min-[40rem]:col-span-2">
      <span class="text-xs opacity-80">{{ t('material.typeName') }}</span>
      <input
        v-model="name"
        type="text"
        class="input input-bordered"
        required
      />
    </label>
    <label class="flex min-w-0 flex-col gap-1">
      <span class="text-xs opacity-80">{{ t('material.shortNameLabel') }}</span>
      <input
        v-model="shortName"
        type="text"
        class="input input-bordered"
        :placeholder="t('material.shortNameOptional')"
      />
    </label>
    <label class="flex min-w-0 flex-col gap-1">
      <span class="text-xs opacity-80">{{ t('material.category') }}</span>
      <input
        v-model="categoryText"
        type="text"
        class="input input-bordered"
        list="material-type-categories"
        :placeholder="t('material.categoryPlaceholder')"
      />
      <datalist id="material-type-categories">
        <option v-for="c in categories" :key="c.id" :value="c.name" />
      </datalist>
    </label>
  </div>

  <label class="flex min-w-0 flex-col gap-1">
    <span class="text-xs opacity-80">{{ t('material.descriptionOptional') }}</span>
    <textarea
      v-model="description"
      class="textarea textarea-bordered"
      rows="2"
    />
  </label>

  <div
    class="rounded-lg border border-base-200 bg-base-200/30 px-3 py-3"
  >
    <div class="grid grid-cols-1 gap-3 min-[40rem]:grid-cols-3">
      <div class="flex min-w-0 flex-col gap-1">
        <span class="text-xs opacity-80">{{ t('material.trackingToggle') }}</span>
        <div
          class="flex h-12 items-center justify-center gap-2 rounded-md bg-base-100/80 px-2 sm:justify-start"
          role="group"
          :aria-label="t('material.trackingToggle')"
        >
          <span
            class="text-sm"
            :class="tracking === 'piece' ? 'font-medium' : 'opacity-60'"
          >
            {{ t('material.trackingPiece') }}
          </span>
          <input
            type="checkbox"
            class="toggle toggle-primary toggle-sm"
            :checked="tracking === 'stock'"
            @change="setTrackingFromToggle(($event.target as HTMLInputElement).checked)"
          />
          <span
            class="text-sm"
            :class="tracking === 'stock' ? 'font-medium' : 'opacity-60'"
          >
            {{ t('material.trackingStock') }}
          </span>
        </div>
      </div>
      <label class="flex min-w-0 flex-col gap-1">
        <span class="text-xs opacity-80">{{ t('material.unitLabel') }}</span>
        <input
          v-model="unit"
          type="text"
          class="input input-bordered bg-base-100"
          :placeholder="t('material.unitOptional')"
          :disabled="tracking === 'piece'"
        />
      </label>
      <label class="flex min-w-0 cursor-pointer flex-col gap-1">
        <span class="text-xs opacity-80">{{ t('material.consumable') }}</span>
        <div class="flex h-12 items-center rounded-md bg-base-100/80 px-2">
          <input v-model="consumable" type="checkbox" class="checkbox checkbox-primary checkbox-sm" />
        </div>
      </label>
    </div>
  </div>

  <MaterialTypeVariantsEditor v-model="variants" />
  </div>
</template>
