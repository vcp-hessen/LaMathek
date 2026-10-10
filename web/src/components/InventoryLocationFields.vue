<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { geocodeAddress } from '../api/geocode'
import InventoryMap from './InventoryMap.vue'

const props = defineProps<{
  defaultLatitude: number
  defaultLongitude: number
}>()

const address = defineModel<string>('address', { required: true })
const notes = defineModel<string>('notes', { required: true })
const latitude = defineModel<number | null>('latitude', { required: true })
const longitude = defineModel<number | null>('longitude', { required: true })

const { t } = useI18n()
const geocodeHint = ref<string | null>(null)
const geocoding = ref(false)

async function onAddressBlur() {
  const query = address.value.trim()
  if (!query) {
    geocodeHint.value = null
    return
  }
  geocoding.value = true
  geocodeHint.value = null
  try {
    const result = await geocodeAddress(query)
    latitude.value = result.latitude
    longitude.value = result.longitude
  } catch {
    geocodeHint.value = t('inventories.geocodeNotFound')
  } finally {
    geocoding.value = false
  }
}
</script>

<template>
  <div class="inventory-form flex flex-col gap-3">
    <label class="flex min-w-0 flex-col gap-1">
      <span class="text-xs opacity-80">{{ t('inventories.addressLabel') }}</span>
      <textarea
        v-model="address"
        class="textarea textarea-bordered"
        rows="2"
        :placeholder="t('inventories.addressOptional')"
        @blur="onAddressBlur"
      />
      <span v-if="geocoding" class="text-xs opacity-70">{{ t('inventories.geocoding') }}</span>
      <span v-else-if="geocodeHint" class="text-xs text-warning">{{ geocodeHint }}</span>
    </label>

    <InventoryMap
      :latitude="latitude"
      :longitude="longitude"
      :default-latitude="props.defaultLatitude"
      :default-longitude="props.defaultLongitude"
      @update:latitude="latitude = $event"
      @update:longitude="longitude = $event"
    />

    <label class="flex min-w-0 flex-col gap-1">
      <span class="text-xs opacity-80">{{ t('inventories.notesLabel') }}</span>
      <textarea
        v-model="notes"
        class="textarea textarea-bordered"
        rows="3"
        :placeholder="t('inventories.notesOptional')"
      />
    </label>
  </div>
</template>
