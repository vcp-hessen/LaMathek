<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchInventoryPermissions } from '../api/inventories'
import { fetchMe, patchMePhone } from '../api/me'
import { deleteLoan, fetchLoan, loanAction, patchLoan, removeLoanLine } from '../api/loans'
import LoanDetailsCollapsible from '../components/loans/LoanDetailsCollapsible.vue'
import LoanLinesSection from '../components/loans/LoanLinesSection.vue'
import LoanPrimaryActions from '../components/loans/LoanPrimaryActions.vue'
import ActionFeedbackBanner from '../components/ActionFeedbackBanner.vue'
import LoanStatusHeader from '../components/loans/LoanStatusHeader.vue'
import { useActiveBox } from '../composables/useActiveBox'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useInventoryCanManage } from '../composables/useInventoryCanManage'
import { useLoanParticipantRoles } from '../composables/useLoanParticipantRoles'
import {
  canCancelUnpackedLoan,
  canDeleteUnreleasedLoan,
  canSkipPickupToReturn,
} from '../utils/loanShortcutEligibility'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const queryClient = useQueryClient()
const { messageFor } = useApiErrorMessage()
const actionError = ref<string | null>(null)

function onMutationError(error: unknown) {
  actionError.value = messageFor(error)
}

const inventoryId = computed(() => Number(route.params.id))
const loanId = computed(() => Number(route.params.loanId))

const { canManage } = useInventoryCanManage(inventoryId)
const { setActiveLoan, activeLoanId } = useActiveBox(inventoryId)

watch(
  loanId,
  (id) => {
    if (Number.isFinite(id)) setActiveLoan(id)
  },
  { immediate: true },
)

const { data: me } = useQuery({ queryKey: ['me'], queryFn: fetchMe })

const { data: loan, isLoading } = useQuery({
  queryKey: ['loan', loanId],
  queryFn: () => fetchLoan(loanId.value),
  enabled: () => Number.isFinite(loanId.value),
})

const {
  isLoanBorrower,
  canActAsManager,
  canEditBorrowerStammdaten,
  canParticipateInLineWorkflow,
  useManagerWorkflowSteps,
} = useLoanParticipantRoles(me, loan, canManage)

const { data: permissionUsers } = useQuery({
  queryKey: ['inventory-permissions', inventoryId],
  queryFn: () => fetchInventoryPermissions(inventoryId.value),
  enabled: () => Number.isFinite(inventoryId.value) && canActAsManager.value,
})

const selectedLineIds = ref<number[]>([])
const phoneForRequest = ref('')

const editPickupNote = ref('')
const editReturnNote = ref('')

watch(
  loan,
  (value) => {
    if (!value) return
    editPickupNote.value = value.pickupNote ?? ''
    editReturnNote.value = value.returnNote ?? ''
    selectedLineIds.value = []
  },
  { immediate: true },
)

watch(me, (value) => {
  if (value?.phone) phoneForRequest.value = value.phone
})

const isDraftPhase = computed(() => loan.value?.phase === 'draft')
const isClosedPhase = computed(() => loan.value?.phase === 'closed')
const isPermanent = computed(() => loan.value?.kind === 'permanent')

function toggleLine(id: number, checked: boolean) {
  if (checked) {
    if (!selectedLineIds.value.includes(id)) {
      selectedLineIds.value = [...selectedLineIds.value, id]
    }
  } else {
    selectedLineIds.value = selectedLineIds.value.filter((x) => x !== id)
  }
}

function selectLines(ids: number[]) {
  if (!ids.length) return
  const set = new Set(selectedLineIds.value)
  for (const id of ids) set.add(id)
  selectedLineIds.value = [...set]
}

function deselectLines(ids: number[]) {
  if (!ids.length) return
  const remove = new Set(ids)
  selectedLineIds.value = selectedLineIds.value.filter((id) => !remove.has(id))
}

function linesMatching(...statuses: string[]) {
  return (loan.value?.lines ?? []).filter((l) => statuses.includes(l.status))
}

function selectedMatching(...statuses: string[]) {
  const allowed = new Set(linesMatching(...statuses).map((l) => l.id))
  return selectedLineIds.value.filter((id) => allowed.has(id))
}

function lineIdsForAction(override: number[] | undefined, ...statuses: string[]) {
  if (override?.length) return override
  return selectedMatching(...statuses)
}

async function invalidate() {
  await queryClient.invalidateQueries({ queryKey: ['loan', loanId.value] })
  await queryClient.invalidateQueries({ queryKey: ['loans', inventoryId.value] })
}

const patchMetaMutation = useMutation({
  mutationFn: (payload: Record<string, unknown>) => patchLoan(loanId.value, payload),
  onSuccess: async () => {
    actionError.value = null
    await invalidate()
  },
  onError: onMutationError,
})

const requestMutation = useMutation({
  mutationFn: async () => {
    if (isLoanBorrower.value && !(me.value?.phone ?? '').trim()) {
      await patchMePhone(phoneForRequest.value.trim())
      await queryClient.invalidateQueries({ queryKey: ['me'] })
    }
    const pickupOn = loan.value?.wishPickupOn ?? loan.value?.pickupOn
    const returnOn = loan.value?.wishReturnOn ?? loan.value?.returnOn
    if (!pickupOn) {
      actionError.value = t('loans.requestDatesRequired')
      return Promise.reject(new Error('dates_required'))
    }
    if (!isPermanent.value && !returnOn) {
      actionError.value = t('loans.requestDatesRequired')
      return Promise.reject(new Error('dates_required'))
    }
    return loanAction(loanId.value, 'request', {
      wishPickupOn: pickupOn,
      wishReturnOn: isPermanent.value ? null : returnOn,
    })
  },
  onSuccess: async () => {
    actionError.value = null
    await invalidate()
  },
  onError: (error) => {
    if (error instanceof Error && error.message === 'dates_required') return
    onMutationError(error)
  },
})

function runLineAction(action: string, lineIds: number[], extra: Record<string, unknown> = {}) {
  if (!lineIds.length) throw new Error('no_lines_selected')
  return loanAction(loanId.value, action, { lineIds, ...extra })
}

const actionMutation = useMutation({
  mutationFn: (args: { action: string; lineIds: number[]; extra?: Record<string, unknown> }) =>
    runLineAction(args.action, args.lineIds, args.extra ?? {}),
  onSuccess: async () => {
    actionError.value = null
    selectedLineIds.value = []
    await invalidate()
  },
  onError: onMutationError,
})

const confirmMutation = useMutation({
  mutationFn: (overrideLineIds?: number[]) => {
    const lineIds = overrideLineIds ?? selectedMatching('requested')
    const contactUserId = loan.value?.contactUserId
    if (contactUserId == null) {
      actionError.value = t('loans.contactRequiredForConfirm')
      return Promise.reject(new Error('contact_required'))
    }
    const pickupOn = loan.value?.pickupOn?.trim()
    const returnOn = loan.value?.returnOn?.trim()
    if (!pickupOn) {
      actionError.value = t('loans.errors.pickup_required')
      return Promise.reject(new Error('dates_required'))
    }
    if (!isPermanent.value && !returnOn) {
      actionError.value = t('loans.errors.return_required')
      return Promise.reject(new Error('dates_required'))
    }
    return loanAction(loanId.value, 'confirm', { lineIds })
  },
  onSuccess: async () => {
    actionError.value = null
    selectedLineIds.value = []
    await invalidate()
  },
  onError: (error) => {
    if (error instanceof Error && error.message === 'contact_required') return
    if (error instanceof Error && error.message === 'dates_required') return
    onMutationError(error)
  },
})

const declineMutation = useMutation({
  mutationFn: (entries: { lineId: number; reason: string }[]) => {
    return loanAction(loanId.value, 'decline', { entries })
  },
  onSuccess: async () => {
    actionError.value = null
    selectedLineIds.value = []
    await invalidate()
  },
  onError: onMutationError,
})

const entryActionMutation = useMutation({
  mutationFn: (args: {
    action: string
    entries: { lineId: number; reason?: string; returnedQuantity?: number }[]
  }) => {
    return loanAction(loanId.value, args.action, { entries: args.entries })
  },
  onSuccess: async () => {
    actionError.value = null
    selectedLineIds.value = []
    await invalidate()
  },
  onError: onMutationError,
})

const removeMutation = useMutation({
  mutationFn: (lineId: number) => removeLoanLine(loanId.value, lineId),
  onSuccess: async () => {
    actionError.value = null
    await invalidate()
  },
  onError: onMutationError,
})

const loanLines = computed(() => loan.value?.lines ?? [])

const showDeleteShortcut = computed(
  () =>
    isLoanBorrower.value &&
    loan.value != null &&
    canDeleteUnreleasedLoan(loanLines.value, loan.value.phase),
)

const showCancelShortcut = computed(
  () =>
    canParticipateInLineWorkflow.value &&
    loan.value?.phase === 'active' &&
    canCancelUnpackedLoan(loanLines.value),
)

const showSkipPickupShortcut = computed(
  () =>
    canParticipateInLineWorkflow.value &&
    loan.value?.phase !== 'closed' &&
    canSkipPickupToReturn(loanLines.value),
)

const showNotifyAddedShortcut = computed(
  () =>
    canParticipateInLineWorkflow.value &&
    loan.value?.phase === 'active' &&
    loan.value?.hasUnnotifiedRequestedLines === true,
)

const notifyAddedMutation = useMutation({
  mutationFn: () => loanAction(loanId.value, 'notify-added'),
  onSuccess: async () => {
    actionError.value = null
    await invalidate()
  },
  onError: onMutationError,
})

const deleteLoanMutation = useMutation({
  mutationFn: () => deleteLoan(loanId.value),
  onSuccess: async () => {
    actionError.value = null
    if (activeLoanId.value === loanId.value) {
      setActiveLoan(null)
    }
    await queryClient.invalidateQueries({ queryKey: ['loans', inventoryId.value] })
    await router.push({ name: 'inventory-loans', params: { id: String(inventoryId.value) } })
  },
  onError: onMutationError,
})

const cancelLoanMutation = useMutation({
  mutationFn: () => loanAction(loanId.value, 'cancel'),
  onSuccess: async () => {
    actionError.value = null
    await invalidate()
  },
  onError: onMutationError,
})

const skipPickupMutation = useMutation({
  mutationFn: () => loanAction(loanId.value, 'skip-pickup'),
  onSuccess: async () => {
    actionError.value = null
    await invalidate()
  },
  onError: onMutationError,
})

const shortcutPending = computed(
  () =>
    deleteLoanMutation.isPending.value ||
    cancelLoanMutation.isPending.value ||
    skipPickupMutation.isPending.value,
)

function onShortcutDelete() {
  if (!window.confirm(t('loans.shortcutDeleteConfirm'))) return
  deleteLoanMutation.mutate()
}

function onShortcutCancel() {
  if (!window.confirm(t('loans.shortcutCancelConfirm'))) return
  cancelLoanMutation.mutate()
}

function onShortcutSkipPickup() {
  if (!window.confirm(t('loans.shortcutSkipPickupConfirm'))) return
  skipPickupMutation.mutate()
}

const needsPhoneBeforeRequest = computed(
  () =>
    isLoanBorrower.value &&
    isDraftPhase.value &&
    !(me.value?.phone ?? '').trim(),
)

const materialActionError = computed(() => {
  if (!actionError.value || !loan.value) return null
  const hasLines = (loan.value.lines?.length ?? 0) > 0
  if (!hasLines || !canParticipateInLineWorkflow.value) return null
  return actionError.value
})

const requestActionError = computed(() => {
  if (!actionError.value || materialActionError.value) return null
  if (!isDraftPhase.value || !isLoanBorrower.value) return null
  return actionError.value
})

const globalActionError = computed(() => {
  if (!actionError.value) return null
  if (materialActionError.value || requestActionError.value) return null
  return actionError.value
})

</script>

<template>
  <div class="app-page">
    <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
    <template v-else-if="loan">
      <LoanStatusHeader
        :loan="loan"
        :can-manage="canManage"
        :use-manager-workflow-steps="useManagerWorkflowSteps"
        :can-edit-borrower="canEditBorrowerStammdaten"
        :permission-users="permissionUsers ?? []"
        :is-loan-borrower="isLoanBorrower"
        :show-delete-shortcut="showDeleteShortcut"
        :show-cancel-shortcut="showCancelShortcut"
        :show-skip-pickup-shortcut="showSkipPickupShortcut"
        :show-notify-added-shortcut="showNotifyAddedShortcut"
        :notify-added-pending="notifyAddedMutation.isPending.value"
        :shortcut-pending="shortcutPending"
        @use-as-box="setActiveLoan(loan.id)"
        @meta-saved="invalidate()"
        @shortcut-delete="onShortcutDelete"
        @shortcut-cancel="onShortcutCancel"
        @shortcut-skip-pickup="onShortcutSkipPickup"
        @shortcut-notify-added="notifyAddedMutation.mutate()"
      />

      <LoanLinesSection
        :loan="loan"
        :inventory-id="inventoryId"
        :can-manage="canActAsManager"
        :is-loan-borrower="isLoanBorrower"
        :can-participate-in-line-workflow="canParticipateInLineWorkflow"
        :selected-line-ids="selectedLineIds"
        :confirm-pending="confirmMutation.isPending.value"
        :decline-pending="declineMutation.isPending.value"
        :action-pending="actionMutation.isPending.value"
        :entry-action-pending="entryActionMutation.isPending.value"
        :action-message="materialActionError"
        @select-lines="selectLines"
        @deselect-lines="deselectLines"
        @toggle-line="toggleLine"
        @confirm="(lineIds) => confirmMutation.mutate(lineIds)"
        @decline="(entries) => declineMutation.mutate(entries)"
        @withdraw="
          (lineIds) =>
            actionMutation.mutate({
              action: 'withdraw',
              lineIds: lineIdsForAction(lineIds, 'requested', 'confirmed'),
            })
        "
        @pack="
          (lineIds) =>
            actionMutation.mutate({
              action: 'pack',
              lineIds: lineIdsForAction(lineIds, 'confirmed'),
            })
        "
        @unpack="
          (lineIds) =>
            actionMutation.mutate({
              action: 'unpack',
              lineIds: lineIdsForAction(lineIds, 'packed'),
            })
        "
        @not-packed="
          (entries) =>
            entryActionMutation.mutate({
              action: 'mark-not-packed',
              entries,
            })
        "
        @pickup="
          (lineIds) =>
            actionMutation.mutate({
              action: 'pickup',
              lineIds: lineIdsForAction(lineIds, 'packed'),
            })
        "
        @undo-pickup="
          (lineIds) =>
            actionMutation.mutate({
              action: 'undo-pickup',
              lineIds: lineIdsForAction(lineIds, 'picked_up'),
            })
        "
        @not-picked-up="
          (entries) =>
            entryActionMutation.mutate({
              action: 'mark-not-picked-up',
              entries,
            })
        "
        @report-return="
          (lineIds) =>
            actionMutation.mutate({
              action: 'report-return',
              lineIds: lineIdsForAction(lineIds, 'picked_up'),
            })
        "
        @restock="
          (entries) =>
            entryActionMutation.mutate({
              action: 'restock',
              entries,
            })
        "
        @record-loss="
          (entries) =>
            entryActionMutation.mutate({
              action: 'record-loss',
              entries,
            })
        "
        @remove-line="removeMutation.mutate($event)"
      />

      <LoanPrimaryActions
        v-if="loan.lines.length > 0"
        :loan="loan"
        :is-borrower="isLoanBorrower"
        :needs-phone-before-request="needsPhoneBeforeRequest"
        :phone-for-request="phoneForRequest"
        :request-pending="requestMutation.isPending.value"
        :action-message="requestActionError"
        @update:phone-for-request="phoneForRequest = $event"
        @request="requestMutation.mutate()"
      />

      <LoanDetailsCollapsible
        :loan="loan"
        :can-manage="canActAsManager"
        :is-loan-borrower="isLoanBorrower"
        :can-participate-in-line-workflow="canParticipateInLineWorkflow"
        :is-closed-phase="isClosedPhase"
        :is-permanent="isPermanent"
        :edit-pickup-note="editPickupNote"
        :edit-return-note="editReturnNote"
        :patch-pending="patchMetaMutation.isPending.value"
        @update:edit-pickup-note="editPickupNote = $event"
        @update:edit-return-note="editReturnNote = $event"
        @save-pickup-note="patchMetaMutation.mutate({ pickupNote: editPickupNote })"
        @save-return-note="patchMetaMutation.mutate({ returnNote: editReturnNote })"
        @photos-change="queryClient.invalidateQueries({ queryKey: ['loan', loanId] })"
      />

      <ActionFeedbackBanner :message="globalActionError" @dismiss="actionError = null" />
    </template>
  </div>
</template>
