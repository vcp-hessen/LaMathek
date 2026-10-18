<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  createDamageRepair,
  createPieceDamage,
  deletePiece,
  fetchMaterialTypes,
  fetchPiece,
  fetchPieceJournal,
  postPieceFoundAgain,
  updatePiece,
} from '../api/material'
import type { Damage, PieceDetail } from '../schemas/material'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useInventoryCanManage } from '../composables/useInventoryCanManage'
import JournalSection from '../components/journal/JournalSection.vue'
import MaterialDetailsSection from '../components/material/MaterialDetailsSection.vue'
import MaterialItemMetadataFields from '../components/material/MaterialItemMetadataFields.vue'
import {
  emptyItemMetadataDraft,
  itemMetadataFromRecord,
  itemMetadataToWritePayload,
  type ItemMetadataDraft,
} from '../utils/materialItemValue'
import AddToBoxButton from '../components/loans/AddToBoxButton.vue'
import PhotoGallery from '../components/PhotoGallery.vue'
import SuperuserDestructiveDelete from '../components/SuperuserDestructiveDelete.vue'
import VariantAxisSelects from '../components/VariantAxisSelects.vue'
import { syncVariantMapKeys } from '../utils/variantDisplay'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { messageFor } = useApiErrorMessage()
const queryClient = useQueryClient()

const pieceId = computed(() => Number(route.params.pieceId))
const inventoryId = computed(() => Number(route.params.id))
const { canManage } = useInventoryCanManage(inventoryId)

const { data: materialTypes } = useQuery({
  queryKey: ['materialTypes', inventoryId],
  queryFn: () => fetchMaterialTypes(inventoryId.value),
  enabled: () => Number.isFinite(inventoryId.value),
})

const { data: piece, isLoading } = useQuery({
  queryKey: ['piece', pieceId],
  queryFn: () => fetchPiece(pieceId.value),
  enabled: () => Number.isFinite(pieceId.value),
})

const { data: journalEntries, isLoading: journalLoading } = useQuery({
  queryKey: ['piece-journal', pieceId],
  queryFn: () => fetchPieceJournal(pieceId.value),
  enabled: () => Number.isFinite(pieceId.value),
})

const editPieceName = ref('')
const editVariant = ref<Record<string, string>>({})
const editMeta = ref<ItemMetadataDraft>(emptyItemMetadataDraft())
const savedEdit = ref<string | null>(null)
const stammdatenError = ref<string | null>(null)

const editSelectedType = computed(() =>
  (materialTypes.value ?? []).find((mt) => mt.id === piece.value?.materialTypeId),
)

const editTypeAxes = computed(() => editSelectedType.value?.variants ?? [])

function variantPayload(axes: { label: string; values: string[] }[], map: Record<string, string>) {
  if (!axes.length) return undefined
  const payload: Record<string, string> = {}
  for (const axis of axes) {
    const value = map[axis.label]?.trim()
    if (value) payload[axis.label] = value
  }
  return payload
}

function stammdatenSnapshot() {
  return JSON.stringify({
    name: editPieceName.value,
    variant: variantPayload(editTypeAxes.value, editVariant.value) ?? null,
    meta: editMeta.value,
  })
}

const editDirty = computed(
  () => savedEdit.value !== null && stammdatenSnapshot() !== savedEdit.value,
)

function loadStammdatenFromPiece(p: PieceDetail) {
  editPieceName.value = p.name
  const mt = (materialTypes.value ?? []).find((row) => row.id === p.materialTypeId)
  editVariant.value = mt ? syncVariantMapKeys(p.variant, mt.variants) : { ...p.variant }
  editMeta.value = itemMetadataFromRecord(p)
  savedEdit.value = stammdatenSnapshot()
  stammdatenError.value = null
}

watch(
  [piece, materialTypes],
  () => {
    if (piece.value) loadStammdatenFromPiece(piece.value)
  },
  { immediate: true },
)

const damageRecordedOn = ref(new Date().toISOString().slice(0, 10))
const damageNote = ref('')
const damageSevere = ref(false)

const repairNotes = ref<Record<number, string>>({})
const repairDates = ref<Record<number, string>>({})

async function invalidatePiece() {
  await queryClient.invalidateQueries({ queryKey: ['piece', pieceId.value] })
}

async function invalidate() {
  await invalidatePiece()
}

const updateMutation = useMutation({
  mutationFn: () =>
    updatePiece(pieceId.value, {
      name: editPieceName.value,
      variant: variantPayload(editTypeAxes.value, editVariant.value),
      ...itemMetadataToWritePayload(editMeta.value, { includeStatus: true }),
    }),
  onSuccess: async () => {
    stammdatenError.value = null
    savedEdit.value = stammdatenSnapshot()
    await invalidatePiece()
    await queryClient.invalidateQueries({ queryKey: ['pieces', inventoryId.value] })
  },
  onError: (error) => {
    stammdatenError.value = messageFor(error)
  },
})

const deleteMutation = useMutation({
  mutationFn: () => deletePiece(pieceId.value),
  onSuccess: async () => {
    await queryClient.invalidateQueries({ queryKey: ['pieces', inventoryId.value] })
    await router.push(`/inventories/${inventoryId.value}/material`)
  },
  onError: (error) => {
    stammdatenError.value = messageFor(error)
  },
})

const foundAgainReason = ref('')

const foundAgainMutation = useMutation({
  mutationFn: () =>
    postPieceFoundAgain(pieceId.value, {
      reason: foundAgainReason.value.trim(),
    }),
  onSuccess: async () => {
    foundAgainReason.value = ''
    await invalidatePiece()
  },
  onError: (error) => {
    stammdatenError.value = messageFor(error)
  },
})

const damageMutation = useMutation({
  mutationFn: () =>
    createPieceDamage(pieceId.value, {
      recordedOn: damageRecordedOn.value,
      severe: damageSevere.value,
      note: damageNote.value.trim() || undefined,
    }),
  onSuccess: async () => {
    damageNote.value = ''
    damageSevere.value = false
    await invalidate()
  },
})

function repairDateFor(damage: Damage): string {
  return repairDates.value[damage.id] ?? new Date().toISOString().slice(0, 10)
}

function setRepairDate(damageId: number, value: string) {
  repairDates.value[damageId] = value
}

const repairMutation = useMutation({
  mutationFn: (damage: Damage) =>
    createDamageRepair(damage.id, {
      recordedOn: repairDateFor(damage),
      note: repairNotes.value[damage.id]?.trim() || undefined,
    }),
  onSuccess: invalidate,
})

function damageStatusLabel(damage: Damage): string {
  if (damage.open && damage.severe) return t('damage.statusOpenSevere')
  if (damage.open) return t('damage.statusOpen')
  return t('damage.statusRepaired')
}
</script>

<template>
  <div class="app-page space-y-6">
    <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
    <template v-else-if="piece">
      <div class="flex justify-end">
        <AddToBoxButton
          :inventory-id="inventoryId"
          :piece-id="piece.id"
          size="md"
        />
      </div>
      <MaterialDetailsSection
        :form-error="stammdatenError"
        :saving="updateMutation.isPending.value"
        :dirty="editDirty"
        :readonly="!canManage"
        @save="updateMutation.mutate()"
      >
        <fieldset :disabled="!canManage" class="space-y-3 border-0 p-0">
        <label class="flex min-w-0 flex-col gap-1">
          <span class="text-xs opacity-80">{{ t('material.pieceName') }}</span>
          <input
            v-model="editPieceName"
            type="text"
            class="input input-bordered input-sm w-full"
            required
          />
        </label>
        <label class="flex min-w-0 max-w-md flex-col gap-1">
          <span class="text-xs opacity-80">{{ t('material.pieceType') }}</span>
          <select class="select select-bordered select-sm w-full" disabled>
            <option>{{ piece.materialTypeName }}</option>
          </select>
        </label>
        <VariantAxisSelects
          v-if="editTypeAxes.length"
          v-model="editVariant"
          :axes="editTypeAxes"
          compact
        />
        <p v-if="piece.setName" class="text-sm text-base-content/70">
          {{ t('sets.onSet', { name: piece.setName }) }}
        </p>
        <p v-if="piece.lost" class="text-sm">
          <span class="badge badge-error badge-sm">{{ t('material.pieceLost') }}</span>
        </p>
        <div
          v-if="canManage && piece.foundAgainEligible"
          class="flex max-w-md flex-col gap-2 rounded-md border border-base-300 p-3"
        >
          <p class="text-sm font-medium">{{ t('material.foundAgainTitle') }}</p>
          <label class="flex flex-col gap-1 text-sm">
            <span>{{ t('material.foundAgainReason') }}</span>
            <textarea
              v-model="foundAgainReason"
              class="textarea textarea-bordered textarea-sm"
              rows="2"
              required
            />
          </label>
          <button
            type="button"
            class="btn btn-primary btn-sm w-fit"
            :disabled="!foundAgainReason.trim() || foundAgainMutation.isPending.value"
            @click="foundAgainMutation.mutate()"
          >
            {{ t('material.foundAgainAction') }}
          </button>
        </div>
        <MaterialItemMetadataFields
          v-model:acquired-year="editMeta.acquiredYear"
          v-model:note="editMeta.note"
          v-model:source="editMeta.source"
          v-model:serial-number="editMeta.serialNumber"
          v-model:new-value-euro="editMeta.newValueEuro"
          v-model:status="editMeta.status"
          show-status
        />
        </fieldset>
        <template #delete>
          <SuperuserDestructiveDelete
            v-if="canManage"
            :label="t('material.pieceDelete')"
            :warning="t('destructive.pieceWarning')"
            :disabled="deleteMutation.isPending.value"
            @confirmed="deleteMutation.mutate()"
          />
        </template>
      </MaterialDetailsSection>

      <section class="app-section gap-4 border-b border-base-200 pb-6 last:border-b-0">
        
          <h2 class="app-page-title text-base">{{ t('photos.heading') }}</h2>
          <PhotoGallery
            :owner="{ kind: 'piece', pieceId: piece.id }"
            :photos="piece.photos ?? []"
            :readonly="!canManage"
            @change="invalidate"
          />
      </section>

      <section class="app-section gap-4 border-b border-base-200 pb-6 last:border-b-0">
        <JournalSection
          :title="t('journal.pieceHeading')"
          :entries="journalEntries"
          :loading="journalLoading"
        />
      </section>

      <section class="app-section gap-4 border-b border-base-200 pb-6 last:border-b-0">
        
          <h2 class="app-page-title text-base">{{ t('damage.historyHeading') }}</h2>
          <ul v-if="piece.damages.length" class="list-none space-y-3 text-sm">
            <li
              v-for="damage in piece.damages"
              :key="damage.id"
              class="rounded-lg border border-base-200 bg-base-200/30 p-3"
            >
              <div class="flex flex-wrap justify-between gap-2">
                <span class="font-medium">{{ damage.recordedOn }}</span>
                <span class="text-xs opacity-80">{{ damageStatusLabel(damage) }}</span>
              </div>
              <p v-if="damage.note" class="mt-2 text-sm opacity-90">{{ damage.note }}</p>
              <div class="mt-3">
                <PhotoGallery
                  :owner="{ kind: 'damage', damageId: damage.id }"
                  :photos="damage.photos ?? []"
                  readonly
                  @change="invalidate"
                />
              </div>
              <p v-if="damage.repair" class="mt-2 text-xs opacity-80">
                {{ t('damage.repairedOn', { date: damage.repair.recordedOn }) }}
                <template v-if="damage.repair.note"> · {{ damage.repair.note }}</template>
              </p>
              <form
                v-if="canManage && damage.open"
                class="mt-4 space-y-3 border-t border-base-200 pt-4"
                @submit.prevent="repairMutation.mutate(damage)"
              >
                <label class="flex min-w-0 flex-col gap-1 sm:max-w-xs">
                  <span class="text-xs opacity-80">{{ t('damage.repairRecordedOn') }}</span>
                  <input
                    type="date"
                    class="input input-bordered input-sm w-full"
                    :value="repairDateFor(damage)"
                    required
                    @input="setRepairDate(damage.id, ($event.target as HTMLInputElement).value)"
                  />
                </label>
                <label class="flex min-w-0 flex-col gap-1">
                  <span class="text-xs opacity-80">{{ t('damage.repairNote') }}</span>
                  <input
                    v-model="repairNotes[damage.id]"
                    type="text"
                    class="input input-bordered input-sm w-full"
                    :placeholder="t('damage.repairNoteOptional')"
                  />
                </label>
                <div class="flex justify-end">
                  <button
                    type="submit"
                    class="btn btn-primary btn-sm"
                    :disabled="repairMutation.isPending.value"
                  >
                    {{ t('damage.submitRepair') }}
                  </button>
                </div>
              </form>
            </li>
          </ul>
          <p v-else class="text-sm opacity-70">{{ t('damage.historyEmpty') }}</p>
      </section>

      <section
        v-if="canManage"
        class="app-section gap-4 border-b border-base-200 pb-6 last:border-b-0"
      >
          <h2 class="app-page-title text-base">{{ t('damage.newHeading') }}</h2>
          <form class="space-y-3" @submit.prevent="damageMutation.mutate()">
            <label class="flex min-w-0 flex-col gap-1 sm:max-w-xs">
              <span class="text-xs opacity-80">{{ t('damage.recordedOn') }}</span>
              <input
                v-model="damageRecordedOn"
                type="date"
                class="input input-bordered w-full"
                required
              />
            </label>
            <label class="flex min-w-0 flex-col gap-1">
              <span class="text-xs opacity-80">{{ t('damage.note') }}</span>
              <textarea
                v-model="damageNote"
                class="textarea textarea-bordered w-full"
                rows="3"
                :placeholder="t('damage.noteOptional')"
              />
            </label>
            <label class="flex cursor-pointer items-center gap-3">
              <input v-model="damageSevere" type="checkbox" class="checkbox checkbox-sm" />
              <span class="text-sm">{{ t('damage.severe') }}</span>
            </label>
            <div class="flex justify-end gap-2 pt-1">
              <button
                type="submit"
                class="btn btn-primary btn-sm"
                :disabled="damageMutation.isPending.value"
              >
                {{ t('damage.submit') }}
              </button>
            </div>
          </form>
      </section>
    </template>
  </div>
</template>
