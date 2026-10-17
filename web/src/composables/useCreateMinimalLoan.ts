import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { createLoan } from '../api/loans'
import { fetchMe } from '../api/me'
import { useActiveLoanStore } from '../stores/activeLoan'

export function useCreateMinimalLoan(inventoryId: number) {
  const queryClient = useQueryClient()
  const activeLoanStore = useActiveLoanStore()

  const mutation = useMutation({
    mutationFn: async () => {
      const me = await queryClient.fetchQuery({ queryKey: ['me'], queryFn: fetchMe })
      if (!me) throw new Error('not_authenticated')
      return createLoan(inventoryId, {
        groupName: '—',
        borrowerUserId: me.id,
        kind: 'short',
      })
    },
    onSuccess: async (loan) => {
      activeLoanStore.setActiveLoanId(inventoryId, loan.id)
      await queryClient.invalidateQueries({ queryKey: ['loans', inventoryId] })
      await queryClient.invalidateQueries({ queryKey: ['loan-draft', inventoryId] })
      await queryClient.invalidateQueries({ queryKey: ['loan', loan.id] })
    },
  })

  return mutation
}
