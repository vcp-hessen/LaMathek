<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { FunnelIcon } from '@heroicons/vue/24/outline'
import type { VariantAxisCatalogEntry } from '../../utils/pieceVariantFilters'
import type { VariantColumnFilterValue } from './piecesTableSetup'

const props = withDefaults(
  defineProps<{
    catalog: VariantAxisCatalogEntry[]
    modelValue: VariantColumnFilterValue
    toolbar?: boolean
  }>(),
  { toolbar: true },
)

const emit = defineEmits<{
  'update:modelValue': [value: VariantColumnFilterValue]
}>()

const { t } = useI18n()
const axisToAdd = ref('')
const detailsRef = ref<HTMLDetailsElement | null>(null)

const activeValueCount = computed(() =>
  Object.values(props.modelValue).reduce((count, values) => count + values.length, 0),
)

const axisLabels = computed(() => Object.keys(props.modelValue))

const addableAxes = computed(() =>
  props.catalog.filter((entry) => !axisLabels.value.includes(entry.label)),
)

function catalogValuesForLabel(label: string): string[] {
  return props.catalog.find((entry) => entry.label === label)?.values ?? []
}

function isChecked(label: string, value: string): boolean {
  return props.modelValue[label]?.includes(value) ?? false
}

function setChecked(label: string, value: string, checked: boolean) {
  const current = props.modelValue[label] ?? []
  const nextValues = checked
    ? current.includes(value)
      ? current
      : [...current, value]
    : current.filter((v) => v !== value)
  emit('update:modelValue', { ...props.modelValue, [label]: nextValues })
}

function addAxis() {
  const label = axisToAdd.value.trim()
  if (!label || props.modelValue[label] !== undefined) return
  emit('update:modelValue', { ...props.modelValue, [label]: [] })
  axisToAdd.value = ''
}

function removeAxis(label: string) {
  const next = { ...props.modelValue }
  delete next[label]
  emit('update:modelValue', next)
}

function onPickAxisChange() {
  addAxis()
}

function closeOnClickOutside(event: MouseEvent) {
  const root = detailsRef.value
  if (!root?.open) return
  const target = event.target
  if (target instanceof Node && root.contains(target)) return
  root.open = false
}

function closeOnEscape(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  const root = detailsRef.value
  if (root?.open) root.open = false
}

onMounted(() => {
  document.addEventListener('click', closeOnClickOutside, true)
  document.addEventListener('keydown', closeOnEscape)
})

onUnmounted(() => {
  document.removeEventListener('click', closeOnClickOutside, true)
  document.removeEventListener('keydown', closeOnEscape)
})
</script>

<template>
  <details
    v-if="catalog.length"
    ref="detailsRef"
    class="dropdown dropdown-end pieces-variant-filter"
    @click.stop
    @keydown.stop
  >
    <summary
      :class="
        toolbar
          ? 'btn btn-sm btn-outline gap-1.5 font-normal'
          : 'btn btn-ghost btn-xs h-auto min-h-0 gap-1 px-1 font-semibold normal-case'
      "
    >
      <FunnelIcon v-if="toolbar" class="size-4 shrink-0 opacity-70" aria-hidden="true" />
      {{ t('material.piecesFilterVariant') }}
      <span v-if="activeValueCount > 0" class="badge badge-primary badge-sm">
        {{ activeValueCount }}
      </span>
    </summary>
    <div
      class="dropdown-content z-50 w-72 max-h-[min(20rem,70vh)] overflow-y-auto rounded-box border border-base-200 bg-base-100 p-3 shadow-lg"
      @click.stop
    >
      <p class="mb-3 text-xs leading-snug opacity-70">{{ t('material.piecesVariantFilterHelp') }}</p>
      <select
        v-model="axisToAdd"
        class="select select-bordered select-sm mb-3 w-full"
        :disabled="!addableAxes.length"
        @change="onPickAxisChange"
      >
        <option value="">{{ t('material.piecesVariantFilterPickAxis') }}</option>
        <option v-for="entry in addableAxes" :key="entry.label" :value="entry.label">
          {{ entry.label }}
        </option>
      </select>
      <div
        v-for="label in axisLabels"
        :key="label"
        class="mb-3 rounded-lg border border-base-200 bg-base-200/30 p-2 last:mb-0"
      >
        <div class="mb-2 flex items-center justify-between gap-2">
          <span class="text-xs font-semibold">{{ label }}</span>
          <button
            type="button"
            class="btn btn-ghost btn-xs h-auto min-h-0 px-1 py-0"
            @click="removeAxis(label)"
          >
            {{ t('material.piecesVariantFilterRemove', { label }) }}
          </button>
        </div>
        <div class="flex flex-wrap gap-x-3 gap-y-1">
          <label
            v-for="value in catalogValuesForLabel(label)"
            :key="value"
            class="flex cursor-pointer items-center gap-1.5 text-sm"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-sm"
              :checked="isChecked(label, value)"
              @change="setChecked(label, value, ($event.target as HTMLInputElement).checked)"
            />
            <span>{{ value }}</span>
          </label>
        </div>
      </div>
    </div>
  </details>
</template>
