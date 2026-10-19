<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, reactive } from 'vue'
import { useI18n } from 'vue-i18n'

import { fetchStockLosses, resolveStockLoss } from '../../api/material'
import { useApiErrorMessage } from '../../composables/useApiErrorMessage'
import type { StockLoss } from '../../schemas/material'

/** Verluste and Verbrauch booked on one Mengenposten, with found-again and write-off (D0009). */
const props = defineProps<{
  inventoryId: number
  materialTypeId: number
  lotId: number
  canManage: boolean
}>()

const emit = defineEmits<{ changed: [] }>()

const { t } = useI18n()
const { messageFor } = useApiErrorMessage()
const queryClient = useQueryClient()

const queryKey = computed(() => ['stock-losses', props.inventoryId, props.materialTypeId])
const { data: losses } = useQuery({
  queryKey,
  queryFn: () => fetchStockLosses(props.inventoryId, props.materialTypeId),
  enabled: () => props.canManage,
})

const lotLosses = computed(() => (losses.value ?? []).filter((l) => l.stockLotId === props.lotId))

const drafts = reactive<Record<number, { reason: string; quantity: number; error: string | null }>>(
  {},
)

function draftFor(loss: StockLoss) {
  drafts[loss.id] ??= { reason: '', quantity: loss.quantity, error: null }
  return drafts[loss.id]
}

const resolve = useMutation({
  mutationFn: ({ loss, action }: { loss: StockLoss; action: 'found-again' | 'write-off' }) => {
    const draft = draftFor(loss)
    return resolveStockLoss(props.inventoryId, loss.id, action, {
      reason: draft.reason.trim(),
      ...(action === 'found-again' ? { quantity: draft.quantity } : {}),
    })
  },
  onSuccess: async (_result, { loss }) => {
    delete drafts[loss.id]
    await queryClient.invalidateQueries({ queryKey: queryKey.value })
    emit('changed')
  },
  onError: (error, { loss }) => {
    draftFor(loss).error = messageFor(error)
  },
})

function statusText(loss: StockLoss): string {
  if (loss.open) return t('material.lossOpen')
  return loss.resolution ? t(`damage.resolution.${loss.resolution}`) : ''
}
</script>

<template>
  <section
    v-if="canManage"
    class="app-section gap-3 border-b border-base-200 pb-6 last:border-b-0"
  >
    <h2 class="app-page-title text-base">{{ t('material.lossesHeading') }}</h2>
    <p v-if="!lotLosses.length" class="text-sm opacity-70">{{ t('material.lossesEmpty') }}</p>
    <ul v-else class="space-y-3">
      <li
        v-for="loss in lotLosses"
        :key="loss.id"
        class="rounded-md border border-base-300 px-3 py-2 text-sm"
      >
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <span>
            <span class="font-medium">{{ loss.quantity }} × {{ t(`material.lossKind.${loss.kind}`) }}</span>
            · {{ loss.recordedOn }}
            <RouterLink
              v-if="loss.loanId"
              :to="{ name: 'loan-detail', params: { id: inventoryId, loanId: loss.loanId } }"
              class="link link-hover"
            >
              · {{ t('material.lossFromLoan') }} #{{ loss.loanId }}
            </RouterLink>
          </span>
          <span class="text-xs" :class="loss.open ? 'text-warning' : 'opacity-70'">
            {{ statusText(loss) }}
          </span>
        </div>
        <p v-if="loss.reason" class="mt-1 opacity-80">{{ loss.reason }}</p>
        <p v-if="loss.resolutionNote" class="mt-1 text-xs opacity-70">
          {{ loss.resolvedOn }} · {{ loss.resolutionNote }}
        </p>
        <form
          v-if="loss.open"
          class="mt-2 flex flex-wrap items-end gap-2"
          @submit.prevent="resolve.mutate({ loss, action: 'found-again' })"
        >
          <label class="flex w-24 flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('material.lossFoundQuantity') }}</span>
            <input
              v-model.number="draftFor(loss).quantity"
              type="number"
              min="1"
              :max="loss.quantity"
              class="input input-bordered input-sm"
            />
          </label>
          <label class="flex min-w-40 flex-1 flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('material.lossResolveReason') }}</span>
            <input
              v-model="draftFor(loss).reason"
              type="text"
              class="input input-bordered input-sm"
              required
            />
          </label>
          <button
            type="submit"
            class="btn btn-primary btn-sm"
            :disabled="!draftFor(loss).reason.trim() || resolve.isPending.value"
          >
            {{ t('material.lossFoundAction') }}
          </button>
          <button
            type="button"
            class="btn btn-outline btn-sm"
            :disabled="!draftFor(loss).reason.trim() || resolve.isPending.value"
            @click="resolve.mutate({ loss, action: 'write-off' })"
          >
            {{ t('material.lossWriteOffAction') }}
          </button>
          <p v-if="draftFor(loss).error" role="alert" class="w-full text-xs text-error">
            {{ draftFor(loss).error }}
          </p>
        </form>
      </li>
    </ul>
  </section>
</template>
