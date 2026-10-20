import { useQuery } from '@tanstack/vue-query'
import { computed, unref, watch, type MaybeRefOrGetter, toValue } from 'vue'
import { fetchLoan, fetchLoans } from '../api/loans'
import type { Loan } from '../schemas/loan'
import { useActiveLoanStore } from '../stores/activeLoan'
import { useInventoryQueryKey } from './useInventoryQueryKey'

export function loanCanHoldLines(phase: Loan['phase']): boolean {
  return phase === 'draft' || phase === 'review' || phase === 'pack'
}

export function useActiveBox(inventoryId: MaybeRefOrGetter<number>) {
  const activeLoanStore = useActiveLoanStore()
  const invId = computed(() => toValue(inventoryId))

  const loansQueryKey = useInventoryQueryKey('loans', () => unref(invId))

  const { data: loans, isLoading: loansLoading } = useQuery({
    queryKey: loansQueryKey,
    queryFn: () => fetchLoans(invId.value),
    enabled: () => Number.isFinite(invId.value),
  })

  const eligibleLoans = computed(() =>
    (loans.value ?? [])
      .filter((loan) => loanCanHoldLines(loan.phase))
      .sort((a, b) => {
        if (a.phase !== b.phase) {
          if (a.phase === 'draft') return -1
          if (b.phase === 'draft') return 1
        }
        return b.id - a.id
      }),
  )

  const activeLoanId = computed(() => {
    const id = invId.value
    if (!Number.isFinite(id)) return null
    const stored = activeLoanStore.getActiveLoanId(id)
    if (stored === null) return null
    const ok = eligibleLoans.value.some((loan) => loan.id === stored)
    return ok ? stored : null
  })

  watch([loans, eligibleLoans, invId], ([loaded, list, id]) => {
    if (!Number.isFinite(id)) return
    // While this Inventar's Verleihe are still loading the list is empty; deciding
    // now would drop the box chosen earlier.
    if (!loaded) return
    const current = activeLoanStore.getActiveLoanId(id)
    if (current !== null && !list.some((loan) => loan.id === current)) {
      activeLoanStore.clearActiveLoan(id)
      return
    }
    if (current !== null) return
    const drafts = list.filter((loan) => loan.phase === 'draft')
    if (drafts.length === 1) {
      activeLoanStore.setActiveLoanId(id, drafts[0].id)
    }
  })

  const { data: activeLoanDetail, isLoading: activeDetailLoading } = useQuery({
    queryKey: computed(() => ['loan', activeLoanId.value]),
    queryFn: () => fetchLoan(activeLoanId.value!),
    enabled: () => activeLoanId.value != null,
  })

  const activeLoanSummary = computed(() => {
    const id = activeLoanId.value
    if (id === null) return null
    return eligibleLoans.value.find((loan) => loan.id === id) ?? null
  })

  const lineCount = computed(() => activeLoanDetail.value?.lines.length ?? 0)

  const canAddLines = computed(() => {
    const loan = activeLoanDetail.value
    if (!loan) return activeLoanSummary.value != null && loanCanHoldLines(activeLoanSummary.value.phase)
    return loanCanHoldLines(loan.phase)
  })

  function setActiveLoan(loanId: number | null) {
    const id = invId.value
    if (!Number.isFinite(id)) return
    if (loanId === null) activeLoanStore.clearActiveLoan(id)
    else activeLoanStore.setActiveLoanId(id, loanId)
  }

  return {
    loansLoading,
    eligibleLoans,
    activeLoanId,
    activeLoanSummary,
    activeLoanDetail,
    activeDetailLoading,
    lineCount,
    canAddLines,
    setActiveLoan,
  }
}

export type ActiveBoxContext = ReturnType<typeof useActiveBox>
