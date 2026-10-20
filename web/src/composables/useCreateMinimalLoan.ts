import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { type MaybeRefOrGetter, toValue } from 'vue'

import { queryKeys } from '../api/queryKeys'
import { createLoan } from '../api/loans'
import { fetchMe } from '../api/me'
import { useActiveLoanStore } from '../stores/activeLoan'

/** Creates an empty Verleih (the new box) in the Inventar current at call time. */
export function useCreateMinimalLoan(inventoryId: MaybeRefOrGetter<number>) {
  const queryClient = useQueryClient()
  const activeLoanStore = useActiveLoanStore()

  const mutation = useMutation({
    mutationFn: async () => {
      const me = await queryClient.fetchQuery({ queryKey: queryKeys.me, queryFn: fetchMe })
      if (!me) throw new Error('not_authenticated')
      return createLoan(toValue(inventoryId), {
        borrowerUserId: me.id,
        kind: 'short',
      })
    },
    onSuccess: async (loan) => {
      activeLoanStore.setActiveLoanId(loan.inventoryId, loan.id)
      await queryClient.invalidateQueries({ queryKey: ['loans', loan.inventoryId] })
      await queryClient.invalidateQueries({ queryKey: ['loan-draft', loan.inventoryId] })
      await queryClient.invalidateQueries({ queryKey: ['loan', loan.id] })
    },
  })

  return mutation
}
