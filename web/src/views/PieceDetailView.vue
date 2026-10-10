<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { createDamageRepair, createPieceDamage, fetchPiece } from '../api/material'
import type { Damage } from '../schemas/material'

const route = useRoute()
const { t } = useI18n()
const queryClient = useQueryClient()

const pieceId = computed(() => Number(route.params.pieceId))

const { data: piece, isLoading } = useQuery({
  queryKey: ['piece', pieceId],
  queryFn: () => fetchPiece(pieceId.value),
  enabled: () => Number.isFinite(pieceId.value),
})

const damageRecordedOn = ref(new Date().toISOString().slice(0, 10))
const damageNote = ref('')
const damageSevere = ref(false)

const repairNotes = ref<Record<number, string>>({})
const repairDates = ref<Record<number, string>>({})

async function invalidate() {
  await queryClient.invalidateQueries({ queryKey: ['piece', pieceId.value] })
}

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
      <section class="card bg-base-100 shadow-md">
        <div class="card-body gap-2 text-left">
          <h1 class="card-title text-lg">{{ piece.name }}</h1>
          <p class="text-sm text-base-content/70">
            {{ piece.materialTypeName }}
            <template v-if="piece.variant"> · {{ piece.variant }}</template>
            <template v-if="piece.setName">
              · {{ t('sets.onSet', { name: piece.setName }) }}
            </template>
          </p>
        </div>
      </section>

      <section class="card bg-base-100 shadow-md">
        <div class="card-body gap-4 text-left">
          <h2 class="card-title text-base">{{ t('damage.historyHeading') }}</h2>
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
              <p v-if="damage.repair" class="mt-2 text-xs opacity-80">
                {{ t('damage.repairedOn', { date: damage.repair.recordedOn }) }}
                <template v-if="damage.repair.note"> · {{ damage.repair.note }}</template>
              </p>
              <form
                v-if="damage.open"
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
        </div>
      </section>

      <section class="card bg-base-100 shadow-md">
        <div class="card-body gap-4 text-left">
          <h2 class="card-title text-base">{{ t('damage.newHeading') }}</h2>
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
        </div>
      </section>
    </template>
  </div>
</template>
