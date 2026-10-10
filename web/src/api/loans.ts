import { api } from './client'
import { meSchema, type Me } from '../schemas/me'
import {
  eventSchema,
  groupSchema,
  loanDetailSchema,
  loanSchema,
  type Loan,
  type LoanDetail,
} from '../schemas/loan'

export async function fetchGroups() {
  const response = await api.get('/api/groups')
  return groupSchema.array().parse(response.data)
}

export async function fetchEvents() {
  const response = await api.get('/api/events')
  return eventSchema.array().parse(response.data)
}

export async function fetchVerantwortliche(): Promise<Me[]> {
  const response = await api.get('/api/users/verantwortliche')
  return meSchema.array().parse(response.data)
}

export async function fetchLoans(inventoryId: number): Promise<Loan[]> {
  const response = await api.get(`/api/inventories/${inventoryId}/loans`)
  return loanSchema.array().parse(response.data)
}

export async function createLoan(
  inventoryId: number,
  payload: {
    groupName: string
    responsibleUserId: number
    kind?: 'short' | 'permanent'
    eventName?: string
    startsOn?: string
    endsOn?: string
  },
): Promise<LoanDetail> {
  const response = await api.post(`/api/inventories/${inventoryId}/loans`, payload)
  return loanDetailSchema.parse(response.data)
}

export async function fetchLoan(loanId: number): Promise<LoanDetail> {
  const response = await api.get(`/api/loans/${loanId}`)
  return loanDetailSchema.parse(response.data)
}

export async function addLoanSetAssignmentLines(
  loanId: number,
  setId: number,
): Promise<LoanDetail> {
  const response = await api.post(`/api/loans/${loanId}/lines`, {
    setId,
    scope: 'assignment',
  })
  return loanDetailSchema.parse(response.data)
}

export async function addLoanSetOptionalLines(
  loanId: number,
  setId: number,
): Promise<LoanDetail> {
  const response = await api.post(`/api/loans/${loanId}/lines`, {
    setId,
    scope: 'optionals',
  })
  return loanDetailSchema.parse(response.data)
}

export async function addLoanPieceLine(loanId: number, pieceId: number): Promise<LoanDetail> {
  const response = await api.post(`/api/loans/${loanId}/lines`, { pieceId })
  return loanDetailSchema.parse(response.data)
}

export async function addLoanStockLine(
  loanId: number,
  materialTypeId: number,
  quantity: number,
): Promise<LoanDetail> {
  const response = await api.post(`/api/loans/${loanId}/lines`, {
    materialTypeId,
    quantity,
  })
  return loanDetailSchema.parse(response.data)
}

export async function removeLoanLine(loanId: number, lineId: number): Promise<void> {
  await api.delete(`/api/loans/${loanId}/lines/${lineId}`)
}

export async function handOutLoan(loanId: number): Promise<LoanDetail> {
  const response = await api.post(`/api/loans/${loanId}/hand-out`)
  return loanDetailSchema.parse(response.data)
}

export async function recordLoanReturn(
  loanId: number,
  payload: {
    recordedOn: string
    entries: Array<{
      loanLineId: number
      outcome: 'returned' | 'loss'
      quantity?: number
    }>
  },
): Promise<LoanDetail> {
  const response = await api.post(`/api/loans/${loanId}/returns`, payload)
  return loanDetailSchema.parse(response.data)
}
