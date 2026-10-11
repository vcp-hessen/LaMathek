<script setup lang="ts">
import { photoUrl, type PhotoSize } from '../api/photos'

const props = withDefaults(
  defineProps<{
    photoId: number | null | undefined
    size?: PhotoSize
    alt?: string
    class?: string
  }>(),
  {
    size: '160',
    alt: '',
    class: 'h-10 w-10 rounded object-cover bg-base-200',
  },
)
</script>

<template>
  <img
    v-if="photoId"
    :src="photoUrl(photoId, size)"
    :alt="alt"
    :class="props.class"
    loading="lazy"
  />
</template>
