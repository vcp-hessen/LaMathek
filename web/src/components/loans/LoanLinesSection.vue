<script setup lang="ts">
import { computed, ref, watch, withDefaults } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { LoanDetail } from '../../schemas/loan'
import UiIcon from '../UiIcon.vue'
import LoanLinesDataTable from './LoanLinesDataTable.vue'
import { LOAN_DETAIL_SECTION } from './loanDetailLayout'
import { deriveLineActionContext } from './loanLineActionContext'
import {
  loanWorkflowContextFromLoan,
  resolveEffectiveWorkflowStep,
} from '../../domain/loanWorkflowSteps'
import type { LineRowActionId } from './loanLineRowActions'
import { stageButtonClass } from './loanWorkflowTones'
import type { WorkflowTone } from './loanWorkflowTones'

type ReasonAction = 'decline' | 'notPacked' | 'notPickedUp' | 'recordLoss'

const props = withDefaults(
  defineProps<{
    loan: LoanDetail
    inventoryId: number
    canManage: boolean
    isLoanBorrower: boolean
    canParticipateInLineWorkflow: boolean
    selectedLineIds: number[]
    confirmPending: boolean
    declinePending: boolean
    actionPending: boolean
    entryActionPending: boolean
    actionMessage: string | null
    /** Omit outer section chrome when wrapped by parent (e.g. with pickup/return). */
    nested?: boolean
  }>(),
  { nested: false },
)

const emit = defineEmits<{
  selectLines: [ids: number[]]
  deselectLines: [ids: number[]]
  toggleLine: [id: number, checked: boolean]
  confirm: [lineIds?: number[]]
  decline: [entries: { lineId: number; reason: string }[]]
  withdraw: [lineIds?: number[]]
  pack: [lineIds?: number[]]
  unpack: [lineIds?: number[]]
  notPacked: [entries: { lineId: number; reason: string }[]]
  pickup: [lineIds?: number[]]
  undoPickup: [lineIds?: number[]]
  notPickedUp: [entries: { lineId: number; reason: string }[]]
  reportReturn: [lineIds?: number[]]
  restock: [entries: { lineId: number; returnedQuantity?: number; reason?: string }[]]
  recordLoss: [entries: { lineId: number; reason: string }[]]
  restore: [lineId: number]
  removeLine: [lineId: number]
}>()

const { t } = useI18n()

const loanLines = computed(() => props.loan.lines ?? [])

const selectedLines = computed(() =>
  loanLines.value.filter((line) => props.selectedLineIds.includes(line.id)),
)

const workflowContext = computed(() => loanWorkflowContextFromLoan(props.loan))

const effectiveWorkflowStep = computed(() => resolveEffectiveWorkflowStep(workflowContext.value))

const actionContext = computed(() =>
  deriveLineActionContext(selectedLines.value, effectiveWorkflowStep.value),
)

const showLineToolbar = computed(
  () => props.canParticipateInLineWorkflow && (props.loan.lines?.length ?? 0) > 0,
)

const hasValidLoanDates = computed(() => {
  const pickup = props.loan.pickupOn?.trim()
  const returnDate = props.loan.returnOn?.trim()
  if (props.loan.kind === 'permanent') {
    return Boolean(pickup)
  }
  return Boolean(pickup) && Boolean(returnDate)
})

const confirmDisabled = computed(() => {
  if (props.confirmPending) return true
  if (props.loan.contactUserId == null) return true
  if (!hasValidLoanDates.value) return true
  return false
})

const confirmTitle = computed(() => {
  if (props.loan.contactUserId == null) return t('loans.contactRequiredForConfirm')
  if (!hasValidLoanDates.value) return t('loans.confirmDatesRequired')
  return ''
})

const pendingReasonAction = ref<ReasonAction | null>(null)
const sharedReasonDraft = ref('')
const sharedReasonMissing = ref(false)
const restockQuantityDrafts = ref<Record<number, number>>({})
const restockReasonDraft = ref('')
const restockReasonMissing = ref(false)

const selectedReturnReportedLines = computed(() =>
  loanLines.value.filter(
    (line) =>
      props.selectedLineIds.includes(line.id) && line.status === 'return_reported',
  ),
)

const selectedConsumableRestockLines = computed(() =>
  selectedReturnReportedLines.value.filter(
    (line) => line.kind === 'stock' && line.consumable,
  ),
)

const selectedNonConsumableStockRestockLines = computed(() =>
  selectedReturnReportedLines.value.filter(
    (line) => line.kind === 'stock' && !line.consumable,
  ),
)

const selectedStockRestockLines = computed(() =>
  selectedReturnReportedLines.value.filter((line) => line.kind === 'stock'),
)

const declineToolbarLabelKey = computed(() => {
  const selected = selectedLines.value
  const hasConfirmed = selected.some((line) => line.status === 'confirmed')
  const hasRequested = selected.some((line) => line.status === 'requested')
  if (hasConfirmed && !hasRequested) return 'loans.actionRevokeConfirmWithCount'
  return 'loans.actionDeclineWithCount'
})

const needsRestockPartialReason = computed(() =>
  selectedNonConsumableStockRestockLines.value.some((line) => {
    if (line.kind !== 'stock') return false
    const returned = restockQuantityDrafts.value[line.id] ?? line.quantity
    return returned > 0 && returned < line.quantity
  }),
)

const needsRestockZeroConsumableReason = computed(() =>
  selectedConsumableRestockLines.value.some((line) => {
    if (line.kind !== 'stock') return false
    const returned = restockQuantityDrafts.value[line.id] ?? line.quantity
    return returned === 0
  }),
)

watch(
  () => props.selectedLineIds,
  () => {
    const next = { ...restockQuantityDrafts.value }
    for (const line of selectedReturnReportedLines.value) {
      if (line.kind !== 'stock') continue
      if (next[line.id] == null) next[line.id] = line.quantity
    }
    restockQuantityDrafts.value = next
  },
)

function restockEntries(lineIds: number[]): {
  lineId: number
  returnedQuantity?: number
  reason?: string
}[] {
  const reason = restockReasonDraft.value.trim()
  return lineIds.map((lineId) => {
    const line = loanLines.value.find((row) => row.id === lineId)
    if (line?.kind === 'stock') {
      const returnedQuantity = restockQuantityDrafts.value[lineId] ?? line.quantity
      const entry: { lineId: number; returnedQuantity?: number; reason?: string } = {
        lineId,
        returnedQuantity,
      }
      if (!line.consumable && returnedQuantity < line.quantity) {
        entry.reason = reason
      }
      if (line.consumable && returnedQuantity === 0) {
        entry.reason = reason
      }
      return entry
    }
    return { lineId }
  })
}

function emitRestock(lineIds?: number[]) {
  const ids =
    lineIds ??
    selectedReturnReportedLines.value.map((line) => line.id)
  if (!ids.length) return
  if (needsRestockPartialReason.value && !restockReasonDraft.value.trim()) {
    restockReasonMissing.value = true
    return
  }
  const zeroConsumable = selectedConsumableRestockLines.value.some((line) => {
    if (line.kind !== 'stock') return false
    const returned = restockQuantityDrafts.value[line.id] ?? line.quantity
    return returned === 0
  })
  if (zeroConsumable && !restockReasonDraft.value.trim()) {
    restockReasonMissing.value = true
    return
  }
  restockReasonMissing.value = false
  emit('restock', restockEntries(ids))
}

watch(
  () => props.selectedLineIds,
  () => {
    if (pendingReasonAction.value) {
      const ids = lineIdsForReasonAction(pendingReasonAction.value)
      if (!ids.length) cancelReason()
    }
  },
)

function actionBtnClass(tone: Exclude<WorkflowTone, 'luftgrau'>, solid: boolean) {
  return stageButtonClass(tone, solid)
}

function openReason(action: ReasonAction) {
  pendingReasonAction.value = action
  sharedReasonMissing.value = false
}

function cancelReason() {
  pendingReasonAction.value = null
  sharedReasonDraft.value = ''
  sharedReasonMissing.value = false
}

function lineIdsForReasonAction(action: ReasonAction): number[] {
  const selected = loanLines.value.filter((line) => props.selectedLineIds.includes(line.id))
  if (action === 'decline') {
    return selected.filter((l) => l.status === 'requested' || l.status === 'confirmed').map((l) => l.id)
  }
  if (action === 'notPacked') {
    return selected.filter((l) => l.status === 'packed').map((l) => l.id)
  }
  if (action === 'notPickedUp') {
    return selected.filter((l) => l.status === 'packed').map((l) => l.id)
  }
  return selected
    .filter((l) => l.status === 'picked_up' || l.status === 'return_reported')
    .map((l) => l.id)
}

watch(sharedReasonDraft, () => {
  if (sharedReasonDraft.value.trim()) sharedReasonMissing.value = false
})

function entriesWithReason(lineIds: number[]): { lineId: number; reason: string }[] {
  const reason = sharedReasonDraft.value.trim()
  return lineIds.map((lineId) => ({ lineId, reason }))
}

function submitSharedReason() {
  const action = pendingReasonAction.value
  if (!action) return
  const lineIds = lineIdsForReasonAction(action)
  if (!lineIds.length) return
  const entries = entriesWithReason(lineIds)
  if (entries.some((entry) => !entry.reason)) {
    sharedReasonMissing.value = true
    return
  }
  pendingReasonAction.value = null
  sharedReasonDraft.value = ''
  sharedReasonMissing.value = false
  if (action === 'decline') emit('decline', entries)
  else if (action === 'notPacked') emit('notPacked', entries)
  else if (action === 'notPickedUp') emit('notPickedUp', entries)
  else emit('recordLoss', entries)
}

function rowReasonActionId(id: LineRowActionId): ReasonAction | null {
  if (id === 'decline') return 'decline'
  if (id === 'notPacked') return 'notPacked'
  if (id === 'notPickedUp') return 'notPickedUp'
  if (id === 'recordLoss') return 'recordLoss'
  return null
}

function handleRowAction({ id, lineId }: { id: LineRowActionId; lineId: number }) {
  const lineIds = [lineId]
  const reasonAction = rowReasonActionId(id)
  if (reasonAction) {
    if (!props.selectedLineIds.includes(lineId)) {
      emit('selectLines', [lineId])
    }
    if (pendingReasonAction.value === reasonAction) {
      submitSharedReason()
      return
    }
    openReason(reasonAction)
    return
  }
  switch (id) {
    case 'remove':
      emit('removeLine', lineId)
      break
    case 'confirm':
      emit('confirm', lineIds)
      break
    case 'withdraw':
      emit('withdraw', lineIds)
      break
    case 'pack':
      emit('pack', lineIds)
      break
    case 'unpack':
      emit('unpack', lineIds)
      break
    case 'pickup':
      emit('pickup', lineIds)
      break
    case 'undoPickup':
      emit('undoPickup', lineIds)
      break
    case 'reportReturn':
      emit('reportReturn', lineIds)
      break
    case 'restock':
      emitRestock(lineIds)
      break
    case 'restore':
      emit('restore', lineId)
      break
  }
}

const reasonPending = computed(
  () => props.declinePending || props.entryActionPending,
)

function countLabel(key: string, count: number): string {
  return t(key, { count })
}
</script>

<template>
  <component :is="nested ? 'div' : 'section'" :class="nested ? 'space-y-4' : LOAN_DETAIL_SECTION">
    <h2 class="app-page-title text-base">{{ t('loans.linesHeading') }}</h2>

    <div class="space-y-4 text-sm">
      <LoanLinesDataTable
        v-if="loanLines.length"
        :lines="loanLines"
        :inventory-id="inventoryId"
        :selected-line-ids="selectedLineIds"
        :can-manage="canManage"
        :is-loan-borrower="isLoanBorrower"
        :can-participate="canParticipateInLineWorkflow"
        :confirm-allowed="!confirmDisabled"
        :confirm-blocked-title="confirmTitle"
        :workflow="workflowContext"
        @toggle-line="(id, checked) => emit('toggleLine', id, checked)"
        @select-lines="(ids) => emit('selectLines', ids)"
        @deselect-lines="(ids) => emit('deselectLines', ids)"
        @remove-line="(id) => emit('removeLine', id)"
        @row-action="handleRowAction"
      />
      <div v-else class="space-y-2 opacity-80">
        <p>{{ t('loans.linesEmpty') }}</p>
        <p class="text-sm">{{ t('loans.linesEmptyHint') }}</p>
        <RouterLink
          class="link link-primary text-sm"
          :to="`/inventories/${inventoryId}/material`"
        >
          {{ t('loans.openMaterial') }}
        </RouterLink>
      </div>
    </div>

    <div
      v-if="showLineToolbar"
      class="mt-3 flex flex-col gap-2 rounded-lg border border-base-200 bg-base-200/40 p-3"
    >
      <template v-if="actionContext.kind === 'hint'">
        <p class="text-sm opacity-80">
          {{
            actionContext.hint === 'select'
              ? t('loans.lineActionsSelectRows')
              : actionContext.hint === 'wrong_step'
                ? t('loans.actionBlockedWrongStep')
                : actionContext.hint === 'mixed'
                  ? t('loans.lineActionsMixedStatus')
                  : t('loans.lineActionsNoAction')
          }}
        </p>
      </template>

      <template v-else-if="actionContext.kind === 'review'">
        <div
          v-if="canManage || (isLoanBorrower && actionContext.withdrawCount > 0)"
          class="flex flex-wrap items-center gap-2"
        >
          <template v-if="canManage">
          <button
            v-if="actionContext.confirmCount > 0"
            type="button"
            :class="actionBtnClass('blau', true)"
            :disabled="confirmDisabled"
            :title="confirmTitle"
            @click="emit('confirm')"
          >
            <UiIcon name="check" size-class="size-4" />
            {{ countLabel('loans.actionConfirmWithCount', actionContext.confirmCount) }}
          </button>
          <button
            v-if="actionContext.declineCount > 0"
            type="button"
            :class="actionBtnClass('blau', false)"
            :disabled="declinePending || pendingReasonAction === 'decline'"
            @click="openReason('decline')"
          >
            <UiIcon name="x" size-class="size-4" />
            {{ countLabel(declineToolbarLabelKey, actionContext.declineCount) }}
          </button>
          </template>
          <button
            v-if="(isLoanBorrower || canManage) && actionContext.withdrawCount > 0"
            type="button"
            class="btn btn-ghost btn-sm"
            :disabled="actionPending"
            @click="emit('withdraw')"
          >
            {{ countLabel('loans.actionWithdrawWithCount', actionContext.withdrawCount) }}
          </button>
        </div>
      </template>

      <template v-else-if="actionContext.kind === 'pack'">
        <div class="flex flex-wrap items-center gap-2">
          <button
            v-if="canManage"
            type="button"
            :class="actionBtnClass('wasserblau', true)"
            :disabled="actionPending"
            @click="emit('pack')"
          >
            <UiIcon name="pack" size-class="size-4" />
            {{ countLabel('loans.actionPackWithCount', actionContext.count) }}
          </button>
          <button
            v-if="canManage"
            type="button"
            :class="actionBtnClass('blau', false)"
            :disabled="declinePending || pendingReasonAction === 'decline'"
            @click="openReason('decline')"
          >
            <UiIcon name="x" size-class="size-4" />
            {{ countLabel(declineToolbarLabelKey, actionContext.declineCount) }}
          </button>
          <button
            v-if="isLoanBorrower || canManage"
            type="button"
            class="btn btn-ghost btn-sm"
            :disabled="actionPending"
            @click="emit('withdraw')"
          >
            {{ countLabel('loans.actionWithdrawWithCount', actionContext.withdrawCount) }}
          </button>
        </div>
      </template>

      <template v-else-if="actionContext.kind === 'handover'">
        <div class="flex flex-wrap items-center gap-2">
          <button
            v-if="isLoanBorrower || canManage"
            type="button"
            :class="actionBtnClass('erdbraun', true)"
            :disabled="actionPending"
            @click="emit('pickup')"
          >
            <UiIcon name="pickup" size-class="size-4" />
            {{ countLabel('loans.actionPickupWithCount', actionContext.pickupCount) }}
          </button>
          <button
            v-if="isLoanBorrower || canManage"
            type="button"
            :class="actionBtnClass('erdbraun', false)"
            :disabled="entryActionPending || pendingReasonAction === 'notPickedUp'"
            @click="openReason('notPickedUp')"
          >
            <UiIcon name="pickupOff" size-class="size-4" />
            {{ countLabel('loans.actionNotPickedUpWithCount', actionContext.notPickedUpCount) }}
          </button>
          <button
            v-if="canManage"
            type="button"
            :class="actionBtnClass('wasserblau', false)"
            :disabled="entryActionPending || pendingReasonAction === 'notPacked'"
            @click="openReason('notPacked')"
          >
            <UiIcon name="packOff" size-class="size-4" />
            {{ countLabel('loans.actionNotPackedWithCount', actionContext.notPackedCount) }}
          </button>
          <button
            v-if="canManage"
            type="button"
            class="btn btn-ghost btn-sm"
            :disabled="actionPending"
            @click="emit('unpack')"
          >
            {{ countLabel('loans.actionUnpackWithCount', actionContext.unpackCount) }}
          </button>
        </div>
      </template>

      <template v-else-if="actionContext.kind === 'return'">
        <div
          v-if="
            canManage &&
            (selectedConsumableRestockLines.length || selectedNonConsumableStockRestockLines.length)
          "
          class="flex flex-col gap-2 rounded-lg border border-base-200 bg-base-100/80 p-2"
        >
          <p v-if="selectedConsumableRestockLines.length" class="text-xs opacity-80">
            {{ t('loans.restockConsumableHint') }}
          </p>
          <div
            v-for="line in selectedStockRestockLines"
            :key="line.id"
            class="flex flex-wrap items-center gap-2"
          >
            <span class="min-w-0 flex-1 text-sm">{{ line.materialTypeName }}</span>
            <label class="flex items-center gap-1 text-xs">
              <span>{{ t('loans.restockReturnedOf', { total: line.quantity }) }}</span>
              <input
                v-model.number="restockQuantityDrafts[line.id]"
                type="number"
                class="input input-bordered input-xs w-20"
                min="0"
                :max="line.quantity"
              />
            </label>
          </div>
          <input
            v-if="needsRestockPartialReason || needsRestockZeroConsumableReason"
            v-model="restockReasonDraft"
            type="text"
            class="input input-bordered input-sm w-full"
            :class="{ 'input-error': restockReasonMissing }"
            :placeholder="t('loans.reasonRequiredPlaceholder')"
            :aria-label="t('loans.reason')"
          />
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <template v-if="canManage">
            <button
              type="button"
              :class="actionBtnClass('feuergelb', true)"
              :disabled="actionPending || actionContext.restockCount === 0"
              @click="emitRestock()"
            >
              <UiIcon name="restock" size-class="size-4" />
              {{ countLabel('loans.actionRestockWithCount', actionContext.restockCount) }}
            </button>
            <button
              type="button"
              :class="actionBtnClass('feuerrot', false)"
              :disabled="entryActionPending || actionContext.lossCount === 0 || pendingReasonAction === 'recordLoss'"
              @click="openReason('recordLoss')"
            >
              <UiIcon name="loss" size-class="size-4" />
              {{ countLabel('loans.actionRecordLossWithCount', actionContext.lossCount) }}
            </button>
          </template>
          <button
            v-if="(isLoanBorrower || canManage) && actionContext.pickedUpCount > 0"
            type="button"
            :class="actionBtnClass('feuergelb', true)"
            :disabled="actionPending"
            @click="emit('reportReturn')"
          >
            <UiIcon name="return" size-class="size-4" />
            {{ countLabel('loans.actionReportReturnWithCount', actionContext.pickedUpCount) }}
          </button>
          <button
            v-if="(isLoanBorrower || canManage) && actionContext.undoPickupCount > 0"
            type="button"
            class="btn btn-ghost btn-sm"
            :disabled="actionPending"
            @click="emit('undoPickup')"
          >
            {{ countLabel('loans.actionUndoPickupWithCount', actionContext.undoPickupCount) }}
          </button>
        </div>
        <p
          v-if="
            !canManage &&
            isLoanBorrower &&
            actionContext.pickedUpCount === 0 &&
            actionContext.returnReportedCount > 0
          "
          class="text-sm opacity-80"
        >
          {{ t('loans.lineActionsAwaitingRestock') }}
        </p>
      </template>

      <div
        v-if="pendingReasonAction"
        class="flex flex-wrap items-center gap-2 border-t border-base-200 pt-3"
      >
        <input
          v-model="sharedReasonDraft"
          type="text"
          class="input input-bordered input-sm min-w-[12rem] flex-1"
          :class="{ 'input-error': sharedReasonMissing }"
          :placeholder="t('loans.reasonRequiredPlaceholder')"
          :aria-label="t('loans.reason')"
          :aria-invalid="sharedReasonMissing || undefined"
          @keydown.enter.prevent="submitSharedReason()"
        />
        <button
          type="button"
          class="btn btn-primary btn-sm"
          :disabled="reasonPending"
          @click="submitSharedReason()"
        >
          {{ t('loans.reasonSubmit') }}
        </button>
        <button
          type="button"
          class="btn btn-ghost btn-sm"
          :disabled="reasonPending"
          @click="cancelReason()"
        >
          {{ t('destructive.cancel') }}
        </button>
        <p
          v-if="sharedReasonMissing"
          role="alert"
          class="basis-full text-xs text-error"
        >
          {{ t('loans.lineReasonMissingShort') }}
        </p>
      </div>

      <div
        v-if="actionMessage"
        role="alert"
        class="flex items-start gap-2 rounded-md border border-[#e94653]/50 bg-[#f9c5c9] px-2.5 py-2 text-sm leading-snug"
      >
        <UiIcon name="loss" size-class="size-5 shrink-0 text-[#e94653]" />
        <p class="min-w-0 flex-1 whitespace-pre-line">{{ actionMessage }}</p>
      </div>
    </div>
  </component>
</template>
