<script setup lang="ts">
import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  addLoanPieceLine,
  addLoanSetAssignmentLines,
  addLoanSetOptionalLines,
  addLoanStockLine,
  loanAction,
  removeLoanLine,
} from '../../api/loans'
import { useActiveBox } from '../../composables/useActiveBox'
import type { LoanLine } from '../../schemas/loan'
import { useApiErrorMessage } from '../../composables/useApiErrorMessage'
import WlzIcon from '../WlzIcon.vue'

const OPEN_LINE_STATUSES = new Set<string>([
  'draft',
  'requested',
  'confirmed',
  'packed',
  'picked_up',
  'return_reported',
])

const REMOVABLE_LINE_STATUSES = new Set<string>(['draft', 'requested', 'confirmed'])

const props = defineProps<{
  inventoryId: number
  pieceId?: number
  materialTypeId?: number
  quantity?: number
  setId?: number
  setScope?: 'assignment' | 'optionals'
  pieceIds?: number[]
  stockTypeIds?: number[]
  size?: 'xs' | 'sm' | 'md'
  showLabel?: boolean
  label?: string
}>()

const { t } = useI18n()
const queryClient = useQueryClient()
const { messageFor } = useApiErrorMessage()

const { activeLoanId, activeLoanDetail, canAddLines } = useActiveBox(() => props.inventoryId)

function lineMatches(line: LoanLine) {
  if (!OPEN_LINE_STATUSES.has(line.status)) return false
  if (props.pieceId != null) return line.kind === 'piece' && line.pieceId === props.pieceId
  if (props.setId != null) {
    const role = props.setScope === 'optionals' ? 'optional' : 'assignment'
    if (props.pieceIds != null || props.stockTypeIds != null) {
      if (line.kind === 'piece') return (props.pieceIds ?? []).includes(line.pieceId)
      return (
        line.originSetId === props.setId &&
        line.originSetRole === role &&
        (props.stockTypeIds ?? []).includes(line.materialTypeId)
      )
    }
    return line.originSetId === props.setId && line.originSetRole === role
  }
  if (props.materialTypeId != null) {
    return line.kind === 'stock' && line.materialTypeId === props.materialTypeId
  }
  return false
}

const matchingLines = computed(() =>
  (activeLoanDetail.value?.lines ?? []).filter((line) => lineMatches(line)),
)

const removableLines = computed(() =>
  matchingLines.value.filter((line) => REMOVABLE_LINE_STATUSES.has(line.status)),
)

const inBox = computed(() => {
  if (props.setId != null && (props.pieceIds != null || props.stockTypeIds != null)) {
    const pieces = props.pieceIds ?? []
    const stocks = props.stockTypeIds ?? []
    if (pieces.length + stocks.length === 0) return false
    return (
      pieces.every((pieceId) =>
        matchingLines.value.some((line) => line.kind === 'piece' && line.pieceId === pieceId),
      ) &&
      stocks.every((typeId) =>
        matchingLines.value.some(
          (line) => line.kind === 'stock' && line.materialTypeId === typeId,
        ),
      )
    )
  }
  return matchingLines.value.length > 0
})

const disabled = computed(
  () =>
    activeLoanId.value == null ||
    !canAddLines.value ||
    (inBox.value && removableLines.value.length === 0),
)

const title = computed(() => {
  const action =
    activeLoanId.value == null
      ? t('loans.selectBoxFirst')
      : inBox.value && removableLines.value.length === 0
        ? t('loans.boxFurther')
        : inBox.value
          ? t('loans.removeFromBox')
          : t('loans.addToBox')
  return props.label ? `${action} (${props.label})` : action
})

async function addToBox(loanId: number) {
  if (props.pieceId != null) return addLoanPieceLine(loanId, props.pieceId)
  if (props.setId != null) {
    if (props.setScope === 'optionals') return addLoanSetOptionalLines(loanId, props.setId)
    return addLoanSetAssignmentLines(loanId, props.setId)
  }
  if (props.materialTypeId != null) {
    return addLoanStockLine(loanId, props.materialTypeId, props.quantity ?? 1)
  }
  throw new Error('invalid_payload')
}

async function removeFromBox(loanId: number) {
  const drafts = removableLines.value.filter((line) => line.status === 'draft')
  const withdrawIds = removableLines.value
    .filter((line) => line.status !== 'draft')
    .map((line) => line.id)
  for (const line of drafts) {
    await removeLoanLine(loanId, line.id)
  }
  if (withdrawIds.length > 0) {
    await loanAction(loanId, 'withdraw', { lineIds: withdrawIds })
  }
}

const mutation = useMutation({
  mutationFn: async () => {
    const loanId = activeLoanId.value
    if (loanId == null) throw new Error('no_box')
    if (inBox.value && removableLines.value.length > 0) return removeFromBox(loanId)
    return addToBox(loanId)
  },
  onSuccess: async (_data, _vars, _ctx) => {
    const loanId = activeLoanId.value
    if (loanId != null) {
      await queryClient.invalidateQueries({ queryKey: ['loan', loanId] })
    }
    await queryClient.invalidateQueries({ queryKey: ['loans', props.inventoryId] })
  },
})

const feedback = computed(() => {
  if (mutation.isError.value) return messageFor(mutation.error.value)
  return null
})

const btnClass = computed(() => {
  const size = props.size === 'xs' ? 'btn-xs' : props.size === 'md' ? 'btn-md' : 'btn-sm'
  const tone = inBox.value
    ? 'border-transparent bg-vcp-feuergelb text-vcp-erdbraun hover:bg-vcp-feuergelb/80'
    : 'btn-ghost text-vcp-blau hover:bg-vcp-blau/10'
  return ['btn gap-1', size, tone].join(' ')
})
</script>

<template>
  <div class="inline-flex flex-col items-start gap-0.5">
    <button
      type="button"
      :class="btnClass"
      :disabled="disabled || mutation.isPending.value"
      :title="title"
      @click.stop="mutation.mutate()"
    >
      <WlzIcon :glyph="inBox ? 'full' : 'empty'" size-class="text-sm" tooltip="" />
      <span v-if="showLabel !== false" class="hidden sm:inline">{{ title }}</span>
    </button>
    <p v-if="feedback" class="text-xs" :class="mutation.isError.value ? 'text-error' : 'opacity-70'">
      {{ feedback }}
    </p>
  </div>
</template>
