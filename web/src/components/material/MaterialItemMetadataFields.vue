<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { MaterialItemStatus } from '../../schemas/material'

defineProps<{
  showStatus?: boolean
}>()

const acquiredYear = defineModel<number | ''>('acquiredYear', { required: true })
const note = defineModel<string>('note', { required: true })
const source = defineModel<string>('source', { required: true })
const serialNumber = defineModel<string>('serialNumber', { required: true })
const newValueEuro = defineModel<string>('newValueEuro', { required: true })
const status = defineModel<MaterialItemStatus>('status', { required: false })

const { t } = useI18n()
</script>

<template>
  <div
    class="material-item-metadata grid grid-cols-2 gap-x-3 gap-y-2 border-t border-base-200 pt-3 sm:grid-cols-4"
  >
    <label
      v-if="showStatus"
      class="col-span-2 flex min-w-0 flex-col gap-0.5 sm:col-span-1"
    >
      <span class="text-xs opacity-80">{{ t('material.itemStatus') }}</span>
      <select
        v-model="status"
        class="select select-bordered select-sm w-full min-h-8"
        required
      >
        <option value="active">{{ t('material.itemStatusActive') }}</option>
        <option value="retired">{{ t('material.itemStatusRetired') }}</option>
      </select>
    </label>
    <label class="flex min-w-0 flex-col gap-0.5">
      <span class="text-xs opacity-80">{{ t('material.acquiredYear') }}</span>
      <input
        v-model.number="acquiredYear"
        type="number"
        class="input input-bordered input-sm w-full min-h-8 px-2"
        :placeholder="t('material.optionalEmpty')"
        min="1900"
        :max="new Date().getFullYear() + 1"
      />
    </label>
    <label class="flex min-w-0 flex-col gap-0.5">
      <span class="text-xs opacity-80">{{ t('material.newValueEuro') }}</span>
      <input
        v-model="newValueEuro"
        type="text"
        inputmode="decimal"
        class="input input-bordered input-sm w-full min-h-8 px-2"
        :placeholder="t('material.newValuePlaceholder')"
      />
    </label>
    <label class="col-span-2 flex min-w-0 flex-col gap-0.5 sm:col-span-1">
      <span class="text-xs opacity-80">{{ t('material.serialNumber') }}</span>
      <input
        v-model="serialNumber"
        type="text"
        class="input input-bordered input-sm w-full min-h-8"
        :placeholder="t('material.optionalEmpty')"
      />
    </label>
    <label class="col-span-2 flex min-w-0 flex-col gap-0.5 sm:col-span-2">
      <span class="text-xs opacity-80">{{ t('material.itemSource') }}</span>
      <input
        v-model="source"
        type="text"
        class="input input-bordered input-sm w-full min-h-8"
        :placeholder="t('material.itemSourcePlaceholder')"
      />
    </label>
    <label class="col-span-2 flex min-w-0 flex-col gap-0.5 sm:col-span-2">
      <span class="text-xs opacity-80">{{ t('material.itemNote') }}</span>
      <input
        v-model="note"
        type="text"
        class="input input-bordered input-sm w-full min-h-8"
        :placeholder="t('material.optionalEmpty')"
      />
    </label>
  </div>
</template>
