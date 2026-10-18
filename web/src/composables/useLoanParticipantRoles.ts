import { computed, type Ref } from 'vue'
import type { LoanDetail } from '../schemas/loan'

/**
 * Separates inventory-manager powers from borrower-on-this-loan powers.
 * Same person can hold both; UI must not treat every manager as the borrower.
 */
export function useLoanParticipantRoles(
  me: Ref<{ id: number } | null | undefined>,
  loan: Ref<LoanDetail | undefined>,
  canManageInventory: Ref<boolean | undefined>,
) {
  const isLoanBorrower = computed(
    () =>
      me.value != null &&
      loan.value != null &&
      me.value.id === loan.value.borrowerUserId,
  )

  const canActAsManager = computed(
    () =>
      canManageInventory.value === true &&
      loan.value != null &&
      loan.value.phase !== 'draft',
  )

  const canEditBorrowerStammdaten = computed(
    () =>
      loan.value?.phase === 'draft' &&
      (isLoanBorrower.value || canManageInventory.value === true),
  )

  const canParticipateInLineWorkflow = computed(
    () => canActAsManager.value || isLoanBorrower.value,
  )

  const useManagerWorkflowSteps = computed(() => canActAsManager.value)

  return {
    isLoanBorrower,
    canActAsManager,
    canEditBorrowerStammdaten,
    canParticipateInLineWorkflow,
    useManagerWorkflowSteps,
  }
}
