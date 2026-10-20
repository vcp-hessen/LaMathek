<script setup lang="ts">
import { variantKey } from '../../utils/variantDisplay'
import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
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
import UiIcon from '../UiIcon.vue'
import WlzTriStateButton from '../WlzTriStateButton.vue'
import type { WlzTriState } from '../../utils/wlzTriState'

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
  /** Variant combination of the Mengenposten being added (#12). */
  stockVariant?: Record<string, string>
  /** Lendable quantity of the Mengenposten: default amount and "fully in the box" mark (#11). */
  availableQuantity?: number
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
const { boxActionFeedback } = useApiErrorMessage()

const errorDetail = ref<string | null>(null)
const errorHint = ref<string | null>(null)
const errorAlertId = `add-to-box-error-${Math.random().toString(36).slice(2)}`

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
    return (
      line.kind === 'stock' &&
      line.materialTypeId === props.materialTypeId &&
      variantKey(line.stockVariant) === variantKey(props.stockVariant)
    )
  }
  return false
}

const matchingLines = computed(() =>
  (activeLoanDetail.value?.lines ?? []).filter((line) => lineMatches(line)),
)

const removableLines = computed(() =>
  matchingLines.value.filter((line) => REMOVABLE_LINE_STATUSES.has(line.status)),
)

function setPieceStockCoverage(): { matched: number; total: number } {
  const pieces = props.pieceIds ?? []
  const stocks = props.stockTypeIds ?? []
  let total = 0
  let matched = 0
  for (const pieceId of pieces) {
    total += 1
    if (matchingLines.value.some((line) => line.kind === 'piece' && line.pieceId === pieceId)) {
      matched += 1
    }
  }
  for (const typeId of stocks) {
    total += 1
    if (
      matchingLines.value.some(
        (line) => line.kind === 'stock' && line.materialTypeId === typeId,
      )
    ) {
      matched += 1
    }
  }
  return { matched, total }
}

// --- Menge: choose the amount instead of always adding 1 (#11) ---------------------

const isStock = computed(() => props.materialTypeId != null && props.setId == null)

/** Loose line (not from a Set) whose quantity can still be changed: draft or requested. */
const editableStockLine = computed(() =>
  matchingLines.value.find(
    (line) =>
      line.kind === 'stock' &&
      line.originSetId == null &&
      (line.status === 'draft' || line.status === 'requested'),
  ) as Extract<LoanLine, { kind: 'stock' }> | undefined,
)

const stockInBox = computed(() =>
  matchingLines.value.reduce((sum, line) => sum + (line.kind === 'stock' ? line.quantity : 0), 0),
)

const panelOpen = ref(false)
const panelQuantity = ref(1)
const panelReason = ref('')

const needsReason = computed(() => {
  const line = editableStockLine.value
  return line?.status === 'requested' && panelQuantity.value < line.quantity
})

function openStockPanel() {
  panelQuantity.value =
    editableStockLine.value?.quantity ?? Math.max(1, props.availableQuantity ?? 1)
  panelReason.value = ''
  panelOpen.value = !panelOpen.value
}

const boxFillState = computed((): WlzTriState => {
  if (isStock.value) {
    if (stockInBox.value === 0) return 'off'
    const target = props.availableQuantity ?? 0
    return target > 0 && stockInBox.value < target ? 'partial' : 'on'
  }
  if (props.setId != null && (props.pieceIds != null || props.stockTypeIds != null)) {
    const { matched, total } = setPieceStockCoverage()
    if (total === 0) return 'off'
    if (matched === 0) return 'off'
    if (matched === total) return 'on'
    return 'partial'
  }
  return matchingLines.value.length > 0 ? 'on' : 'off'
})

const inBox = computed(() => boxFillState.value === 'on')

const disabled = computed(
  () =>
    activeLoanId.value == null ||
    !canAddLines.value ||
    (!isStock.value && inBox.value && removableLines.value.length === 0),
)

const actionTitle = computed(() => {
  const action =
    activeLoanId.value == null
      ? t('loans.selectBoxFirst')
      : isStock.value && stockInBox.value > 0
        ? t('loans.box.update')
      : inBox.value && removableLines.value.length === 0
        ? t('loans.boxFurther')
        : inBox.value
          ? t('loans.removeFromBox')
          : t('loans.addToBox')
  return props.label ? `${action} (${props.label})` : action
})

const buttonTitle = computed(() => {
  if (errorHint.value) {
    return `${actionTitle.value} — ${errorHint.value}`
  }
  return actionTitle.value
})

function dismissError() {
  errorDetail.value = null
  errorHint.value = null
  skippedNotice.value = null
  mutation.reset()
}

/** Set pieces the server left out (retired, lost, severely damaged; D0011). */
const skippedNotice = ref<string | null>(null)

async function addToBox(loanId: number) {
  if (props.pieceId != null) return addLoanPieceLine(loanId, props.pieceId)
  if (props.setId != null) {
    if (props.setScope === 'optionals') return addLoanSetOptionalLines(loanId, props.setId)
    return addLoanSetAssignmentLines(loanId, props.setId)
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

type BoxAction = 'toggle' | 'setStock' | 'removeStock'

const mutation = useMutation({
  mutationFn: async (action: BoxAction = 'toggle') => {
    const loanId = activeLoanId.value
    if (loanId == null) throw new Error('no_box')
    if (action === 'setStock') {
      return addLoanStockLine(
        loanId,
        props.materialTypeId!,
        panelQuantity.value,
        props.stockVariant,
        panelReason.value.trim() || undefined,
      )
    }
    if (action === 'removeStock' || (inBox.value && removableLines.value.length > 0)) {
      return removeFromBox(loanId)
    }
    return addToBox(loanId)
  },
  onSuccess: async (result) => {
    errorDetail.value = null
    errorHint.value = null
    panelOpen.value = false
    const skipped = result && 'skippedPieces' in result ? (result.skippedPieces ?? []) : []
    skippedNotice.value = skipped.length
      ? [
          t('loans.warnings.skippedHeading'),
          ...skipped.map((p) => `• ${p.pieceName}: ${t(`loans.warnings.${p.code}`)}`),
        ].join('\n')
      : null
    const loanId = activeLoanId.value
    if (loanId != null) {
      await queryClient.invalidateQueries({ queryKey: ['loan', loanId] })
    }
    await queryClient.invalidateQueries({ queryKey: ['loans', props.inventoryId] })
  },
  onError: (error) => {
    const feedback = boxActionFeedback(error)
    errorHint.value = feedback.hint
    errorDetail.value = feedback.banner
  },
})

const errorRingClass = computed(() =>
  errorDetail.value ? 'ring-2 ring-error/60 ring-offset-1 ring-offset-base-100' : '',
)
</script>

<template>
  <div class="inline-flex max-w-full flex-col items-end gap-1">
    <div class="inline-flex items-center gap-1" :class="errorRingClass">
      <WlzTriStateButton
        :model-value="boxFillState"
        :size="size"
        :title="buttonTitle"
        :cycle-on-click="false"
        :disabled="disabled || mutation.isPending.value"
        @click="isStock ? openStockPanel() : mutation.mutate('toggle')"
      />
      <span v-if="showLabel !== false" class="hidden sm:inline">{{ actionTitle }}</span>
    </div>
    <form
      v-if="isStock && panelOpen"
      class="w-max max-w-[min(18rem,calc(100vw-2rem))] space-y-2 rounded-md border border-base-300 bg-base-100 p-2.5 text-left text-xs shadow-sm"
      @submit.prevent="mutation.mutate('setStock')"
      @keydown.esc="panelOpen = false"
      @click.stop
    >
      <p v-if="stockInBox" class="opacity-70">{{ t('loans.box.inBox', { count: stockInBox }) }}</p>
      <label class="flex items-center gap-2">
        <span>{{ t('loans.box.quantity') }}</span>
        <input
          v-model.number="panelQuantity"
          type="number"
          min="1"
          class="input input-bordered input-xs w-20"
          required
        />
        <span v-if="availableQuantity != null" class="opacity-60">
          {{ t('loans.box.ofAvailable', { count: availableQuantity }) }}
        </span>
      </label>
      <label v-if="needsReason" class="flex flex-col gap-1">
        <span>{{ t('loans.box.reason') }}</span>
        <input v-model="panelReason" type="text" class="input input-bordered input-xs" required />
      </label>
      <div class="flex flex-wrap justify-end gap-1">
        <button
          v-if="removableLines.length"
          type="button"
          class="btn btn-ghost btn-xs"
          :disabled="mutation.isPending.value"
          @click="mutation.mutate('removeStock')"
        >
          {{ t('loans.removeFromBox') }}
        </button>
        <button
          type="submit"
          class="btn btn-primary btn-xs"
          :disabled="mutation.isPending.value || panelQuantity < 1 || (needsReason && !panelReason.trim())"
        >
          {{ editableStockLine ? t('loans.box.update') : t('loans.addToBox') }}
        </button>
      </div>
    </form>
    <div
      v-if="skippedNotice && !errorDetail"
      role="status"
      class="w-max max-w-[min(18rem,calc(100vw-2rem))] rounded-md border border-warning/50 bg-base-100 px-2.5 py-2 text-left text-xs leading-snug shadow-sm"
    >
      <div class="flex items-start gap-2">
        <p class="min-w-0 flex-1 whitespace-pre-line">{{ skippedNotice }}</p>
        <button
          type="button"
          class="btn btn-ghost btn-xs btn-square shrink-0 -mr-1 -mt-0.5"
          :aria-label="t('feedback.dismiss')"
          @click.stop="dismissError"
        >
          <UiIcon name="x" size-class="size-3.5" />
        </button>
      </div>
    </div>
    <div
      v-if="errorDetail"
      :id="errorAlertId"
      role="alert"
      class="w-max max-w-[min(18rem,calc(100vw-2rem))] rounded-md border border-error/40 bg-base-100 px-2.5 py-2 text-left text-xs leading-snug text-error shadow-sm"
    >
      <div class="flex items-start gap-2">
        <p class="min-w-0 flex-1 whitespace-pre-line">{{ errorDetail }}</p>
        <button
          type="button"
          class="btn btn-ghost btn-xs btn-square shrink-0 -mr-1 -mt-0.5 text-error"
          :aria-label="t('feedback.dismiss')"
          @click.stop="dismissError"
        >
          <UiIcon name="x" size-class="size-3.5" />
        </button>
      </div>
    </div>
  </div>
</template>
