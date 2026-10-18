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

export async function fetchBorrowers(): Promise<Me[]> {
  const response = await api.get('/api/users/borrowers')
  return meSchema.array().parse(response.data)
}

export async function fetchLoans(inventoryId: number): Promise<Loan[]> {
  const response = await api.get(`/api/inventories/${inventoryId}/loans`)
  return loanSchema.array().parse(response.data)
}

export async function fetchMyLoans(): Promise<Loan[]> {
  const response = await api.get('/api/me/loans')
  return loanSchema.array().parse(response.data)
}

export async function fetchDraftLoan(
  inventoryId: number,
  borrowerUserId?: number,
): Promise<LoanDetail | null> {
  const params = borrowerUserId ? { borrowerUserId } : {}
  const response = await api.get(`/api/inventories/${inventoryId}/loans/draft`, { params })
  if (response.data === null) return null
  return loanDetailSchema.parse(response.data)
}

export async function createLoan(
  inventoryId: number,
  payload: {
    groupName: string
    borrowerUserId: number
    kind?: 'short' | 'permanent'
    eventName?: string
    pickupOn?: string
    returnOn?: string
  },
): Promise<LoanDetail> {
  const response = await api.post(`/api/inventories/${inventoryId}/loans`, payload)
  return loanDetailSchema.parse(response.data)
}

export async function addDraftLine(
  inventoryId: number,
  payload: Record<string, unknown>,
): Promise<LoanDetail> {
  const response = await api.post(`/api/inventories/${inventoryId}/loans/draft-lines`, payload)
  return loanDetailSchema.parse(response.data)
}

export async function fetchLoan(loanId: number): Promise<LoanDetail> {
  const response = await api.get(`/api/loans/${loanId}`)
  return loanDetailSchema.parse(response.data)
}

export async function patchLoan(
  loanId: number,
  payload: Record<string, unknown>,
): Promise<LoanDetail> {
  const response = await api.patch(`/api/loans/${loanId}`, payload)
  return loanDetailSchema.parse(response.data)
}

export async function loanAction(
  loanId: number,
  action: string,
  payload: Record<string, unknown> = {},
): Promise<LoanDetail> {
  const response = await api.post(`/api/loans/${loanId}/actions/${action}`, payload)
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

export async function restoreLoanLine(loanId: number, lineId: number): Promise<LoanDetail> {
  const response = await api.post(`/api/loans/${loanId}/lines/${lineId}/restore`)
  return loanDetailSchema.parse(response.data)
}

export async function removeLoanLine(loanId: number, lineId: number): Promise<void> {
  await api.delete(`/api/loans/${loanId}/lines/${lineId}`)
}

export async function deleteLoan(loanId: number): Promise<void> {
  await api.delete(`/api/loans/${loanId}`)
}

export type LoanMailPreview = {
  subject: string
  text: string
  html: string
}

export async function fetchLoanMailPreview(
  loanId: number,
  params: {
    action: string
    audience: string
    variant?: string
    mailStep?: string
  },
): Promise<LoanMailPreview> {
  const query: Record<string, string> = {
    action: params.action,
    audience: params.audience,
  }
  if (params.variant) query.variant = params.variant
  if (params.mailStep) query.mailStep = params.mailStep
  const response = await api.get(`/api/loans/${loanId}/mail-preview`, { params: query })
  return response.data as LoanMailPreview
}
