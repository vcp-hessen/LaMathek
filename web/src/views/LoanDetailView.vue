<script setup lang="ts">
import QueryError from '../components/QueryError.vue'
import { useServerSyncedFields } from '../composables/useServerSyncedFields'
import { useMe } from '../composables/useMe'
import { queryKeys } from '../api/queryKeys'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchInventoryPermissions } from '../api/inventories'
import { patchMePhone } from '../api/me'
import {
  deleteLoan,
  fetchLoan,
  fetchLoanJournal,
  loanAction,
  patchLoan,
  removeLoanLine,
  restoreLoanLine,
} from '../api/loans'
import JournalSection from '../components/journal/JournalSection.vue'
import LoanDetailsCollapsible from '../components/loans/LoanDetailsCollapsible.vue'
import LoanLinesSection from '../components/loans/LoanLinesSection.vue'
import LoanPrimaryActions from '../components/loans/LoanPrimaryActions.vue'
import ActionFeedbackBanner from '../components/ActionFeedbackBanner.vue'
import LoanConflictWarnings from '../components/loans/LoanConflictWarnings.vue'
import LoanMailStatus from '../components/loans/LoanMailStatus.vue'
import LoanStatusHeader from '../components/loans/LoanStatusHeader.vue'
import { LOAN_DETAIL_SECTION } from '../components/loans/loanDetailLayout'
import { useActiveBox } from '../composables/useActiveBox'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useInventoryCanManage } from '../composables/useInventoryCanManage'
import { useLoanParticipantRoles } from '../composables/useLoanParticipantRoles'
import {
  buildLoanPhaseRareMenuItems,
  canCancelForLoan,
  canDeleteLoan,
  canSkipPickupForLoan,
  type LoanPhaseRareActionId,
} from '../utils/loanPhaseRareActions'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const queryClient = useQueryClient()
const { loanActionMessageFor } = useApiErrorMessage()
const actionError = ref<string | null>(null)
const actionErrorMultiline = ref(false)

function onMutationError(error: unknown) {
  actionError.value = loanActionMessageFor(error)
  actionErrorMultiline.value = actionError.value?.includes('\n') ?? false
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

const { data: me } = useMe()

const { data: loan, isLoading, isError, error: loadError, refetch: retryLoad } = useQuery({
  queryKey: ['loan', loanId],
  queryFn: () => fetchLoan(loanId.value),
  enabled: () => Number.isFinite(loanId.value),
})

const { data: journalEntries, isLoading: journalLoading } = useQuery({
  // Under ['loan', id] so every loan refresh reloads the journal too.
  queryKey: ['loan', loanId, 'journal'],
  queryFn: () => fetchLoanJournal(loanId.value),
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

const syncNotes = useServerSyncedFields({ editPickupNote, editReturnNote })

watch(
  loan,
  (value, previous) => {
    if (!value) return
    syncNotes(
      { editPickupNote: value.pickupNote ?? '', editReturnNote: value.returnNote ?? '' },
      { force: previous?.id !== value.id },
    )
    selectedLineIds.value = []
  },
  { immediate: true },
)

// An error from the previous Verleih must not stay on the next one.
watch(loanId, () => {
  actionError.value = null
})

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
      await queryClient.invalidateQueries({ queryKey: queryKeys.me })
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

const restoreMutation = useMutation({
  mutationFn: (lineId: number) => restoreLoanLine(loanId.value, lineId),
  onSuccess: async () => {
    actionError.value = null
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

const rareMenuItems = computed(() => {
  if (!loan.value) return []
  return buildLoanPhaseRareMenuItems(loan.value, {
    isLoanBorrower: isLoanBorrower.value,
    canParticipate: canParticipateInLineWorkflow.value,
    showDelete: canDeleteLoan(loan.value, {
      isLoanBorrower: isLoanBorrower.value,
      isSuperuser: me.value?.isSuperuser === true,
    }),
    showCancel: canCancelForLoan(loan.value, canParticipateInLineWorkflow.value),
    showSkipPickup: canSkipPickupForLoan(loan.value, canParticipateInLineWorkflow.value),
  })
})

const completeStepMutation = useMutation({
  mutationFn: () => loanAction(loanId.value, 'complete-step'),
  onSuccess: async () => {
    actionError.value = null
    selectedLineIds.value = []
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
    skipPickupMutation.isPending.value ||
    entryActionMutation.isPending.value,
)

function onShortcutDelete() {
  const confirmKey =
    me.value?.isSuperuser === true
      ? 'loans.shortcutDeleteSuperuserConfirm'
      : 'loans.shortcutDeleteConfirm'
  if (!window.confirm(t(confirmKey))) return
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

function onRareAction(id: LoanPhaseRareActionId, payload?: { reason: string }) {
  if (id === 'delete') {
    onShortcutDelete()
    return
  }
  if (id === 'cancel') {
    onShortcutCancel()
    return
  }
  if (id === 'skipPickup') {
    onShortcutSkipPickup()
    return
  }
  if (id === 'notPickedUpAll') {
    const item = rareMenuItems.value.find((row) => row.id === id)
    const reason = payload?.reason?.trim()
    if (!item?.lineIds?.length || !reason) return
    entryActionMutation.mutate({
      action: 'mark-not-picked-up',
      entries: item.lineIds.map((lineId) => ({ lineId, reason })),
    })
  }
}

const closeBlockedTitle = computed(() => {
  if (loan.value?.phase !== 'draft' || !isLoanBorrower.value) return ''
  if (needsPhoneBeforeRequest.value && !phoneForRequest.value.trim()) return t('loans.phoneRequired')
  const pickupOn = loan.value.wishPickupOn ?? loan.value.pickupOn
  const returnOn = loan.value.wishReturnOn ?? loan.value.returnOn
  if (!pickupOn || (!isPermanent.value && !returnOn)) return t('loans.requestDatesRequired')
  return ''
})

function onCompletePhase() {
  if (loan.value?.phase === 'draft') {
    requestMutation.mutate()
    return
  }
  completeStepMutation.mutate()
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
    <QueryError v-else-if="isError" :error="loadError" @retry="retryLoad()" />
    <template v-else-if="loan">
      <LoanConflictWarnings v-if="loan.warnings?.length" :warnings="loan.warnings" />
      <LoanMailStatus v-if="loan.mails?.length" :loan-id="loan.id" :mails="loan.mails" />

      <LoanStatusHeader
        :loan="loan"
        :can-manage="canManage"
        :use-manager-workflow-steps="useManagerWorkflowSteps"
        :can-edit-borrower="canEditBorrowerStammdaten"
        :permission-users="permissionUsers ?? []"
        :is-loan-borrower="isLoanBorrower"
        :rare-menu-items="rareMenuItems"
        :shortcut-pending="shortcutPending"
        :complete-pending="requestMutation.isPending.value || completeStepMutation.isPending.value"
        :close-blocked-title="closeBlockedTitle"
        @meta-saved="invalidate()"
        @rare-action="onRareAction"
        @complete-phase="onCompletePhase"
      />

      <section :class="LOAN_DETAIL_SECTION">
        <LoanLinesSection
          nested
          :loan="loan"
          :inventory-id="inventoryId"
          :can-manage="canActAsManager"
          :is-loan-borrower="isLoanBorrower"
          :can-participate-in-line-workflow="canParticipateInLineWorkflow"
          :selected-line-ids="selectedLineIds"
          :confirm-pending="confirmMutation.isPending.value"
          :decline-pending="declineMutation.isPending.value"
          :action-pending="actionMutation.isPending.value || restoreMutation.isPending.value"
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
          @restore="restoreMutation.mutate($event)"
          @remove-line="removeMutation.mutate($event)"
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

        <JournalSection
          :title="t('journal.loanHeading')"
          :entries="journalEntries"
          :loading="journalLoading"
        />
      </section>

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

      <ActionFeedbackBanner
        :message="globalActionError"
        :multiline="actionErrorMultiline"
        @dismiss="actionError = null"
      />

      <p v-if="canActAsManager" class="pt-4 text-center">
        <RouterLink
          class="text-xs text-base-content/40 hover:text-base-content/70"
          :to="`/inventories/${inventoryId}/loans/${loanId}/mail-preview`"
        >
          Mail-Vorschau
        </RouterLink>
      </p>
    </template>
  </div>
</template>
