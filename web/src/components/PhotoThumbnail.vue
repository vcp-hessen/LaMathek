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
    class: 'size-10 shrink-0 overflow-hidden rounded bg-base-200',
  },
)
</script>

<template>
  <div v-if="photoId" :class="props.class">
    <img
      :src="photoUrl(photoId, size)"
      :alt="alt"
      class="size-full max-w-none object-cover"
      loading="lazy"
    />
  </div>
</template>
