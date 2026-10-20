<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchMaterialTypes, fetchPieces } from '../api/material'
import SuperuserDestructiveDelete from '../components/SuperuserDestructiveDelete.vue'
import AddToBoxButton from '../components/loans/AddToBoxButton.vue'
import PhotoGallery from '../components/PhotoGallery.vue'
import VariantAxisSelects from '../components/VariantAxisSelects.vue'
import type { SetDetail } from '../schemas/set'
import { stockName } from '../utils/variantDisplay'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useInventoryCanManage } from '../composables/useInventoryCanManage'
import { useInventoryQueryKey } from '../composables/useInventoryQueryKey'
import {
  deleteSet,
  fetchSet,
  updateSet,
  setPieceOnSet,
  upsertSetStockLine,
} from '../api/sets'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const queryClient = useQueryClient()
const { messageFor } = useApiErrorMessage()
const formError = ref<string | null>(null)

const inventoryId = computed(() => Number(route.params.id))
const setId = computed(() => Number(route.params.setId))
const { canManage } = useInventoryCanManage(inventoryId)

const { data: setDetail, isLoading } = useQuery({
  queryKey: ['set', setId],
  queryFn: () => fetchSet(setId.value),
  enabled: () => Number.isFinite(setId.value),
})

const piecesQueryKey = useInventoryQueryKey('pieces', inventoryId)
const materialTypesQueryKey = useInventoryQueryKey('materialTypes', inventoryId)

const { data: pieces } = useQuery({
  queryKey: piecesQueryKey,
  queryFn: () => fetchPieces(inventoryId.value),
  enabled: () => Number.isFinite(inventoryId.value),
})

const { data: materialTypes } = useQuery({
  queryKey: materialTypesQueryKey,
  queryFn: () => fetchMaterialTypes(inventoryId.value),
  enabled: () => Number.isFinite(inventoryId.value),
})

const name = ref('')
const shortName = ref('')
watch(
  setDetail,
  (s) => {
    if (s) {
      name.value = s.name
      shortName.value = s.shortName ?? ''
    }
  },
  { immediate: true },
)

const freePieces = computed(() =>
  (pieces.value ?? []).filter(
    (p) =>
      p.status === 'active' && (p.setId === null || p.setId === setId.value),
  ),
)

const stockTypes = computed(() =>
  (materialTypes.value ?? []).filter((mt) => mt.tracking === 'stock'),
)

const addPieceId = ref<string>('')
const addPieceRole = ref<'assignment' | 'optional'>('assignment')
const addStockTypeId = ref<string>('')
const addStockRole = ref<'assignment' | 'optional'>('optional')
const addStockQty = ref(1)
const addStockVariant = ref<Record<string, string>>({})
const addStockAxes = computed(
  () => stockTypes.value.find((mt) => mt.id === Number(addStockTypeId.value))?.variants ?? [],
)
watch(addStockTypeId, () => {
  addStockVariant.value = {}
})

async function invalidateAll() {
  await queryClient.invalidateQueries({ queryKey: ['set', setId] })
  await queryClient.invalidateQueries({ queryKey: ['pieces', inventoryId] })
  await queryClient.invalidateQueries({ queryKey: ['sets', inventoryId] })
}

const renameMutation = useMutation({
  mutationFn: () =>
    updateSet(setId.value, {
      name: name.value,
      shortName: shortName.value.trim() || null,
    }),
  onSuccess: async () => {
    formError.value = null
    await invalidateAll()
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const deleteMutation = useMutation({
  mutationFn: () => deleteSet(setId.value),
  onSuccess: async () => {
    await invalidateAll()
    await router.push(`/inventories/${inventoryId.value}/sets`)
  },
})

const pieceMutation = useMutation({
  mutationFn: (payload: { pieceId: number; role: 'assignment' | 'optional' | null }) =>
    setPieceOnSet(setId.value, payload.pieceId, payload.role),
  onSuccess: async () => {
    formError.value = null
    addPieceId.value = ''
    await invalidateAll()
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const stockMutation = useMutation({
  mutationFn: () =>
    upsertSetStockLine(setId.value, {
      materialTypeId: Number(addStockTypeId.value),
      role: addStockRole.value,
      quantity: addStockQty.value,
      variant: addStockVariant.value,
    }),
  onSuccess: async () => {
    formError.value = null
    await invalidateAll()
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const removeStockMutation = useMutation({
  mutationFn: (row: SetDetail['assignmentStock'][number]) =>
    upsertSetStockLine(setId.value, {
      materialTypeId: row.materialTypeId,
      role: row.role,
      quantity: 0,
      variant: row.stockVariant,
    }),
  onSuccess: async () => {
    formError.value = null
    await invalidateAll()
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

function removePiece(pieceId: number) {
  pieceMutation.mutate({ pieceId, role: null })
}

function addPiece() {
  if (!addPieceId.value) return
  pieceMutation.mutate({
    pieceId: Number(addPieceId.value),
    role: addPieceRole.value,
  })
}
</script>

<template>
  <div class="app-page space-y-6">
    <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
    <template v-else-if="setDetail">
      <p v-if="formError" class="text-sm text-error">{{ formError }}</p>
      <form
        v-if="canManage"
        class="flex flex-wrap gap-2"
        @submit.prevent="renameMutation.mutate()"
      >
        <input v-model="name" type="text" class="input input-bordered min-w-0 flex-1" required />
        <input
          v-model="shortName"
          type="text"
          class="input input-bordered w-full sm:w-32"
          :placeholder="t('sets.shortNameOptional')"
        />
        <button type="submit" class="btn btn-primary" :disabled="renameMutation.isPending.value">
          {{ t('sets.rename') }}
        </button>
      </form>
      <h1 v-else class="app-page-title">{{ setDetail.name }}</h1>

      <section class="app-section gap-4 border-b border-base-200 pb-6 last:border-b-0">
        
          <h2 class="app-page-title text-base">{{ t('photos.heading') }}</h2>
          <PhotoGallery
            :owner="{ kind: 'set', setId: setDetail.id }"
            :photos="setDetail.photos ?? []"
            :readonly="!canManage"
            @change="() => queryClient.invalidateQueries({ queryKey: ['set', setId] })"
          />
      </section>

      <div class="grid gap-6 md:grid-cols-2">
        <section class="app-section gap-4 border-b border-base-200 pb-6 last:border-b-0">
          
            <div class="flex items-center justify-between gap-2">
              <h2 class="app-page-title text-base">{{ t('sets.assignment') }}</h2>
              <AddToBoxButton
                :inventory-id="inventoryId"
                :set-id="setId"
                set-scope="assignment"
                :piece-ids="setDetail.assignmentPieceIds"
                :stock-type-ids="setDetail.assignmentStockTypeIds"
                :label="t('sets.assignment')"
                size="xs"
                :show-label="false"
              />
            </div>
            <ul class="space-y-1 text-sm">
              <li v-for="p in setDetail.assignmentPieces" :key="p.id" class="flex justify-between gap-2">
                <span>{{ p.name }} <span class="opacity-60">· {{ p.materialTypeName }}</span></span>
                <button
                  v-if="canManage"
                  type="button"
                  class="btn btn-ghost btn-xs"
                  @click="removePiece(p.id)"
                >
                  {{ t('sets.remove') }}
                </button>
              </li>
              <li v-for="row in setDetail.assignmentStock" :key="row.id" class="flex justify-between gap-2">
                <span>{{ stockName(row.materialTypeName, row.stockVariant) }} × {{ row.quantity }}</span>
                <button
                  v-if="canManage"
                  type="button"
                  class="btn btn-ghost btn-xs"
                  :disabled="removeStockMutation.isPending.value"
                  @click="removeStockMutation.mutate(row)"
                >
                  {{ t('sets.remove') }}
                </button>
              </li>
              <li v-if="!setDetail.assignmentPieces.length && !setDetail.assignmentStock.length" class="opacity-60">
                {{ t('sets.listEmpty') }}
              </li>
            </ul>
        </section>

        <section class="app-section gap-4 border-b border-base-200 pb-6 last:border-b-0">
          
            <div class="flex items-center justify-between gap-2">
              <h2 class="app-page-title text-base">{{ t('sets.optionals') }}</h2>
              <AddToBoxButton
                :inventory-id="inventoryId"
                :set-id="setId"
                set-scope="optionals"
                :piece-ids="setDetail.optionalPieceIds"
                :stock-type-ids="setDetail.optionalStockTypeIds"
                :label="t('sets.optionals')"
                size="xs"
                :show-label="false"
              />
            </div>
            <ul class="space-y-1 text-sm">
              <li v-for="p in setDetail.optionalPieces" :key="p.id" class="flex justify-between gap-2">
                <span>{{ p.name }}</span>
                <button
                  v-if="canManage"
                  type="button"
                  class="btn btn-ghost btn-xs"
                  @click="removePiece(p.id)"
                >
                  {{ t('sets.remove') }}
                </button>
              </li>
              <li v-for="row in setDetail.optionalStock" :key="row.id" class="flex justify-between gap-2">
                <span>{{ stockName(row.materialTypeName, row.stockVariant) }} × {{ row.quantity }}</span>
                <button
                  v-if="canManage"
                  type="button"
                  class="btn btn-ghost btn-xs"
                  :disabled="removeStockMutation.isPending.value"
                  @click="removeStockMutation.mutate(row)"
                >
                  {{ t('sets.remove') }}
                </button>
              </li>
              <li v-if="!setDetail.optionalPieces.length && !setDetail.optionalStock.length" class="opacity-60">
                {{ t('sets.listEmpty') }}
              </li>
            </ul>
        </section>
      </div>

      <div
        v-if="canManage"
        class="app-section gap-4 border-b border-base-200 pb-6 last:border-b-0"
      >
          <h2 class="app-page-title text-base">{{ t('sets.addPiece') }}</h2>
          <div class="flex flex-wrap gap-2">
            <select v-model="addPieceId" class="select select-bordered min-w-48 flex-1">
              <option value="">{{ t('sets.pickPiece') }}</option>
              <option v-for="p in freePieces" :key="p.id" :value="String(p.id)">
                {{ p.name }} ({{ p.materialTypeName }})
                <template v-if="p.setId === setId"> — {{ t('sets.onThisSet') }}</template>
              </option>
            </select>
            <select v-model="addPieceRole" class="select select-bordered">
              <option value="assignment">{{ t('sets.assignment') }}</option>
              <option value="optional">{{ t('sets.optionals') }}</option>
            </select>
            <button
              type="button"
              class="btn btn-primary"
              :disabled="!addPieceId || pieceMutation.isPending.value"
              @click="addPiece"
            >
              {{ t('sets.add') }}
            </button>
          </div>
      </div>

      <div
        v-if="canManage && stockTypes.length"
        class="app-section gap-4 border-b border-base-200 pb-6 last:border-b-0"
      >
        
          <h2 class="app-page-title text-base">{{ t('sets.addStock') }}</h2>
          <div class="flex flex-wrap gap-2">
            <select v-model="addStockTypeId" class="select select-bordered min-w-40 flex-1">
              <option value="">{{ t('sets.pickStockType') }}</option>
              <option v-for="mt in stockTypes" :key="mt.id" :value="String(mt.id)">
                {{ mt.name }}
              </option>
            </select>
            <input
              v-model.number="addStockQty"
              type="number"
              min="1"
              class="input input-bordered w-24"
            />
            <VariantAxisSelects
              v-if="addStockAxes.length"
              v-model="addStockVariant"
              :axes="addStockAxes"
              compact
              inline
            />
            <select v-model="addStockRole" class="select select-bordered">
              <option value="assignment">{{ t('sets.assignment') }}</option>
              <option value="optional">{{ t('sets.optionals') }}</option>
            </select>
            <button
              type="button"
              class="btn btn-primary"
              :disabled="!addStockTypeId || stockMutation.isPending.value"
              @click="stockMutation.mutate()"
            >
              {{ t('sets.reserve') }}
            </button>
          </div>
      </div>

      <SuperuserDestructiveDelete
        v-if="canManage"
        :label="t('sets.delete')"
        :warning="t('destructive.setWarning')"
        :disabled="deleteMutation.isPending.value"
        @confirmed="deleteMutation.mutate()"
      />
    </template>
  </div>
</template>
