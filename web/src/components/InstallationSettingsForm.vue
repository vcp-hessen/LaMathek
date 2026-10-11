<script setup lang="ts">
import { toTypedSchema } from '@vee-validate/zod'
import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { useForm } from 'vee-validate'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { geocodeAddress } from '../api/geocode'
import { updateInstallationSettings } from '../api/settings'
import type { InstallationSettings } from '../schemas/settings'
import { installationSettingsPatchSchema } from '../schemas/settings'
import InventoryMap from './InventoryMap.vue'

const props = defineProps<{
  settings: InstallationSettings
}>()

const { t } = useI18n()
const queryClient = useQueryClient()
const geocodeHint = ref<string | null>(null)
const geocoding = ref(false)

const schema = toTypedSchema(installationSettingsPatchSchema)

const { defineField, handleSubmit, isSubmitting, resetForm } = useForm({
  validationSchema: schema,
  initialValues: props.settings,
})

const [title] = defineField('title')
const [subtitle] = defineField('subtitle')
const [legalName] = defineField('legalName')
const [legalAddress] = defineField('legalAddress')
const [email] = defineField('email')
const [website] = defineField('website')
const [phone] = defineField('phone')
const [representedBy] = defineField('representedBy')
const [register] = defineField('register')
const [mapLatitude] = defineField('mapLatitude')
const [mapLongitude] = defineField('mapLongitude')
const [hostName] = defineField('hostName')
const [hostAddress] = defineField('hostAddress')
const [hostPrivacyUrl] = defineField('hostPrivacyUrl')
const [authProviderName] = defineField('authProviderName')
const [authProviderSameHost] = defineField('authProviderSameHost')
const [authorityName] = defineField('authorityName')
const [authorityUrl] = defineField('authorityUrl')

const mapLat = computed({
  get: () => (typeof mapLatitude.value === 'number' ? mapLatitude.value : null),
  set: (value: number | null) => {
    mapLatitude.value = value ?? props.settings.mapLatitude
  },
})
const mapLng = computed({
  get: () => (typeof mapLongitude.value === 'number' ? mapLongitude.value : null),
  set: (value: number | null) => {
    mapLongitude.value = value ?? props.settings.mapLongitude
  },
})

watch(
  () => props.settings,
  (settings) => {
    resetForm({ values: settings })
  },
)

async function onLegalAddressBlur() {
  const query = String(legalAddress.value ?? '').trim()
  if (!query) {
    geocodeHint.value = null
    return
  }
  geocoding.value = true
  geocodeHint.value = null
  try {
    const result = await geocodeAddress(query)
    mapLatitude.value = result.latitude
    mapLongitude.value = result.longitude
  } catch {
    geocodeHint.value = t('inventories.geocodeNotFound')
  } finally {
    geocoding.value = false
  }
}

const mutation = useMutation({
  mutationFn: updateInstallationSettings,
  onSuccess: async () => {
    await queryClient.invalidateQueries({ queryKey: ['settings'] })
  },
})

const onSubmit = handleSubmit(async (values) => {
  await mutation.mutateAsync(values)
  resetForm({ values })
})
</script>

<template>
  <form class="card bg-base-100 shadow-md" @submit="onSubmit">
    <div class="card-body gap-4 p-4 text-left sm:p-6">
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label class="flex min-w-0 flex-col gap-1">
          <span class="text-xs opacity-80">{{ t('settings.titleLabel') }}</span>
          <input v-model="title" type="text" class="input input-bordered input-sm w-full" />
        </label>
        <label class="flex min-w-0 flex-col gap-1">
          <span class="text-xs opacity-80">{{ t('settings.subtitleLabel') }}</span>
          <input v-model="subtitle" type="text" class="input input-bordered input-sm w-full" />
        </label>
      </div>

      <fieldset class="rounded-lg border border-base-200 px-3 pb-3 pt-1">
        <legend class="px-1 text-sm font-medium">{{ t('settings.impressumHeading') }}</legend>
        <div class="mt-2 flex flex-col gap-2">
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <label class="flex min-w-0 flex-col gap-1">
              <span class="text-xs opacity-80">{{ t('settings.legalNameLabel') }}</span>
              <input v-model="legalName" type="text" class="input input-bordered input-sm w-full" />
            </label>
            <label class="flex min-w-0 flex-col gap-1">
              <span class="text-xs opacity-80">{{ t('settings.registerLabel') }}</span>
              <input v-model="register" type="text" class="input input-bordered input-sm w-full" />
            </label>
          </div>
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <label class="flex min-w-0 flex-col gap-1">
              <span class="text-xs opacity-80">{{ t('settings.emailLabel') }}</span>
              <input v-model="email" type="email" class="input input-bordered input-sm w-full" />
            </label>
            <label class="flex min-w-0 flex-col gap-1">
              <span class="text-xs opacity-80">{{ t('settings.phoneLabel') }}</span>
              <input v-model="phone" type="text" class="input input-bordered input-sm w-full" />
            </label>
            <label class="flex min-w-0 flex-col gap-1">
              <span class="text-xs opacity-80">{{ t('settings.websiteLabel') }}</span>
              <input
                v-model="website"
                type="url"
                class="input input-bordered input-sm w-full"
                :placeholder="t('settings.websitePlaceholder')"
              />
            </label>
          </div>
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <label class="flex min-w-0 flex-col gap-1">
              <span class="text-xs opacity-80">{{ t('settings.representedByLabel') }}</span>
              <textarea
                v-model="representedBy"
                class="textarea textarea-bordered textarea-sm w-full min-h-0"
                rows="2"
              />
            </label>
            <label class="flex min-w-0 flex-col gap-1">
              <span class="text-xs opacity-80">{{ t('settings.legalAddressLabel') }}</span>
              <textarea
                v-model="legalAddress"
                class="textarea textarea-bordered textarea-sm w-full min-h-0"
                rows="2"
                @blur="onLegalAddressBlur"
              />
              <span v-if="geocoding" class="text-xs opacity-70">{{ t('inventories.geocoding') }}</span>
              <span v-else-if="geocodeHint" class="text-xs text-warning">{{ geocodeHint }}</span>
            </label>
          </div>
        </div>
      </fieldset>

      <fieldset class="rounded-lg border border-base-200 px-3 pb-3 pt-1">
        <legend class="px-1 text-sm font-medium">{{ t('settings.privacyHeading') }}</legend>
        <p class="mt-1 text-xs opacity-70">{{ t('settings.privacyHint') }}</p>
        <div class="mt-2 flex flex-col gap-2">
          <label class="flex min-w-0 flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('settings.hostNameLabel') }}</span>
            <input v-model="hostName" type="text" class="input input-bordered input-sm w-full" />
          </label>
          <label class="flex min-w-0 flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('settings.hostAddressLabel') }}</span>
            <textarea
              v-model="hostAddress"
              class="textarea textarea-bordered textarea-sm w-full min-h-0"
              rows="2"
            />
          </label>
          <label class="flex min-w-0 flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('settings.hostPrivacyUrlLabel') }}</span>
            <input
              v-model="hostPrivacyUrl"
              type="url"
              class="input input-bordered input-sm w-full"
              :placeholder="t('settings.websitePlaceholder')"
            />
          </label>
          <label class="flex min-w-0 flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('settings.authProviderNameLabel') }}</span>
            <input
              v-model="authProviderName"
              type="text"
              class="input input-bordered input-sm w-full"
            />
          </label>
          <label class="flex cursor-pointer items-center gap-2">
            <input
              v-model="authProviderSameHost"
              type="checkbox"
              class="checkbox checkbox-sm"
            />
            <span class="text-xs">{{ t('settings.authProviderSameHostLabel') }}</span>
          </label>
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <label class="flex min-w-0 flex-col gap-1">
              <span class="text-xs opacity-80">{{ t('settings.authorityNameLabel') }}</span>
              <input
                v-model="authorityName"
                type="text"
                class="input input-bordered input-sm w-full"
              />
            </label>
            <label class="flex min-w-0 flex-col gap-1">
              <span class="text-xs opacity-80">{{ t('settings.authorityUrlLabel') }}</span>
              <input
                v-model="authorityUrl"
                type="url"
                class="input input-bordered input-sm w-full"
                :placeholder="t('settings.websitePlaceholder')"
              />
            </label>
          </div>
        </div>
      </fieldset>

      <fieldset class="space-y-2 rounded-lg border border-base-200 px-3 pb-3 pt-1">
        <legend class="px-1 text-sm font-medium">{{ t('settings.mapCenterHeading') }}</legend>
        <p class="text-xs opacity-70">
          {{ t('settings.mapCenterHint') }}
          {{ t('settings.mapCenterAddressSync') }}
        </p>
        <InventoryMap
          :latitude="mapLat"
          :longitude="mapLng"
          :default-latitude="mapLatitude as number"
          :default-longitude="mapLongitude as number"
          @update:latitude="mapLat = $event"
          @update:longitude="mapLng = $event"
        />
      </fieldset>

      <p v-if="mutation.isError.value" class="text-sm text-error">
        {{ t('settings.saveFailed') }}
      </p>
      <div class="card-actions justify-end">
        <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
          {{ t('settings.save') }}
        </button>
      </div>
    </div>
  </form>
</template>
