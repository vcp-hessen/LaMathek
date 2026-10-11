<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  deletePhoto,
  makeCoverPhoto,
  photoUrl,
  uploadPhoto,
  type PhotoOwner,
} from '../api/photos'
import type { PhotoMeta } from '../schemas/photo'
import { preparePhotoUpload } from '../utils/preparePhotoUpload'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'

const props = defineProps<{
  owner: PhotoOwner
  photos: PhotoMeta[]
}>()

const emit = defineEmits<{
  change: []
}>()

const { t } = useI18n()
const { messageFor } = useApiErrorMessage()

const items = ref<PhotoMeta[]>([])
const error = ref<string | null>(null)
const uploading = ref(false)
const lightboxId = ref<number | null>(null)

watch(
  () => props.photos,
  (value) => {
    items.value = [...value].sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id)
  },
  { immediate: true, deep: true },
)

const sorted = computed(() =>
  [...items.value].sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id),
)

async function onPickFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  error.value = null
  uploading.value = true
  try {
    const blob = await preparePhotoUpload(file)
    const meta = await uploadPhoto(props.owner, blob, file.name)
    items.value = [...items.value, meta]
    emit('change')
  } catch (err) {
    error.value = messageFor(err) || t('photos.uploadFailed')
  } finally {
    uploading.value = false
  }
}

async function remove(photoId: number) {
  error.value = null
  try {
    await deletePhoto(photoId)
    items.value = items.value.filter((p) => p.id !== photoId)
    if (lightboxId.value === photoId) lightboxId.value = null
    emit('change')
  } catch (err) {
    error.value = messageFor(err) || t('photos.deleteFailed')
  }
}

async function setCover(photoId: number) {
  error.value = null
  try {
    await makeCoverPhoto(photoId)
    items.value = items.value.map((p) => ({
      ...p,
      sortOrder: p.id === photoId ? 0 : p.sortOrder + 1,
    }))
    emit('change')
  } catch (err) {
    error.value = messageFor(err) || t('photos.coverFailed')
  }
}
</script>

<template>
  <div class="space-y-3">
    <div class="flex flex-wrap items-center gap-2">
      <label class="btn btn-outline btn-sm">
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp,image/heic,image/heif"
          class="hidden"
          :disabled="uploading"
          @change="onPickFile"
        />
        {{ uploading ? t('photos.uploading') : t('photos.add') }}
      </label>
      <p v-if="error" class="text-sm text-error">{{ error }}</p>
    </div>
    <div v-if="sorted.length" class="flex flex-wrap gap-2">
      <div
        v-for="(photo, index) in sorted"
        :key="photo.id"
        class="relative flex flex-col gap-1"
      >
        <button
          type="button"
          class="block overflow-hidden rounded-lg border border-base-300"
          @click="lightboxId = photo.id"
        >
          <img
            :src="photoUrl(photo.id, '160')"
            alt=""
            class="h-20 w-20 object-cover"
            loading="lazy"
          />
        </button>
        <div class="flex flex-wrap gap-1">
          <button
            v-if="index > 0"
            type="button"
            class="btn btn-ghost btn-xs"
            @click="setCover(photo.id)"
          >
            {{ t('photos.makeCover') }}
          </button>
          <button type="button" class="btn btn-ghost btn-xs text-error" @click="remove(photo.id)">
            {{ t('photos.remove') }}
          </button>
        </div>
        <span v-if="index === 0" class="text-xs opacity-70">{{ t('photos.cover') }}</span>
      </div>
    </div>
    <p v-else class="text-sm opacity-60">{{ t('photos.empty') }}</p>

    <dialog v-if="lightboxId" class="modal modal-open" @click.self="lightboxId = null">
      <div class="modal-box max-w-3xl p-2">
        <img :src="photoUrl(lightboxId, 'full')" alt="" class="max-h-[80vh] w-full object-contain" />
      </div>
      <form method="dialog" class="modal-backdrop">
        <button type="button" @click="lightboxId = null">close</button>
      </form>
    </dialog>
  </div>
</template>
