<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { createSet, fetchSets } from '../api/sets'
import { useInventoryQueryKey } from '../composables/useInventoryQueryKey'
import PhotoThumbnail from './PhotoThumbnail.vue'

const props = defineProps<{ inventoryId: number }>()

const { t } = useI18n()
const queryClient = useQueryClient()
const newName = ref('')
const newShortName = ref('')

const setsQueryKey = useInventoryQueryKey('sets', () => props.inventoryId)

const { data: sets, isLoading } = useQuery({
  queryKey: setsQueryKey,
  queryFn: () => fetchSets(props.inventoryId),
})

const createMutation = useMutation({
  mutationFn: () =>
    createSet(props.inventoryId, {
      name: newName.value,
      shortName: newShortName.value.trim() || null,
    }),
  onSuccess: async () => {
    newName.value = ''
    newShortName.value = ''
    await queryClient.invalidateQueries({ queryKey: ['sets', props.inventoryId] })
  },
})

const sortedSets = computed(() =>
  [...(sets.value ?? [])].sort((a, b) => a.name.localeCompare(b.name, 'de')),
)
</script>

<template>
  <div class="card bg-base-100 shadow-md">
    <div class="card-body gap-4 text-left">
      <h2 class="card-title text-lg">{{ t('sets.heading') }}</h2>
      <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
      <ul v-else class="menu rounded-box bg-base-200/50">
        <li v-for="set in sortedSets" :key="set.id">
          <RouterLink :to="`/inventories/${inventoryId}/sets/${set.id}`" class="flex items-center gap-3">
            <PhotoThumbnail :photo-id="set.coverPhotoId" />
            <span>
              <span v-if="set.shortName">{{ set.shortName }} · </span>{{ set.name }}
            </span>
          </RouterLink>
        </li>
        <li v-if="!sortedSets.length" class="px-4 py-3 text-sm opacity-70">
          {{ t('sets.empty') }}
        </li>
      </ul>
      <form
        class="flex flex-col gap-2 border-t border-base-200 pt-4 sm:flex-row sm:flex-wrap"
        @submit.prevent="createMutation.mutate()"
      >
        <input
          v-model="newShortName"
          type="text"
          class="input input-bordered w-full sm:w-28"
          :placeholder="t('sets.shortNameOptional')"
        />
        <input
          v-model="newName"
          type="text"
          class="input input-bordered min-w-0 flex-1"
          :placeholder="t('sets.newName')"
          required
        />
        <button type="submit" class="btn btn-primary" :disabled="createMutation.isPending.value">
          {{ t('sets.create') }}
        </button>
      </form>
    </div>
  </div>
</template>
