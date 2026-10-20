// Arranging a journey's past through the real API, as the signed-in person, so the
// test can click only the part it is about. Each call fails the test on an error.
import { expect, type Page } from '@playwright/test'

import { CSRF, isoDay, signInAs, type Persona } from './fixtures.ts'

type Json = Record<string, unknown>
type Line = { id: number; status: string; kind: string; materialTypeName: string; stockVariant?: Record<string, string> }
export type LoanDetail = { id: number; phase: string; lines: Line[] }

export class Api {
  private readonly page: Page

  constructor(page: Page) {
    this.page = page
  }

  async get<T = unknown>(path: string): Promise<T> {
    const response = await this.page.request.get(path)
    expect(response.ok(), `GET ${path}: ${await response.text()}`).toBe(true)
    return (await response.json()) as T
  }

  async send<T = unknown>(method: 'post' | 'patch' | 'put', path: string, body: Json = {}): Promise<T> {
    const response = await this.page.request[method](path, { data: body, headers: CSRF })
    expect(response.ok(), `${method.toUpperCase()} ${path}: ${await response.text()}`).toBe(true)
    return (await response.json()) as T
  }

  async userId(name: string): Promise<number> {
    const users = await this.get<{ id: number; name: string }[]>('/api/users')
    return users.find((user) => user.name === name)!.id
  }

  async materialTypeId(inventoryId: number, name: string): Promise<number> {
    const types = await this.get<{ id: number; name: string }[]>(`/api/inventories/${inventoryId}/material-types`)
    return types.find((type) => type.name === name)!.id
  }

  async pieceId(inventoryId: number, name: string): Promise<number> {
    const pieces = await this.get<{ id: number; name: string }[]>(`/api/inventories/${inventoryId}/pieces`)
    return pieces.find((piece) => piece.name === name)!.id
  }
}

/** Every open line of the loan in `status`. */
function idsIn(loan: LoanDetail, status: string): number[] {
  return loan.lines.filter((line) => line.status === status).map((line) => line.id)
}

/**
 * A Verleih of `lines`, requested by the borrower for [start, end] (days from today)
 * and walked by the real API up to `until`.
 */
export async function arrangeLoan(
  page: Page,
  options: {
    inventoryId: number
    title: string
    lines: Json[]
    start: number
    end: number
    until: 'review' | 'pack' | 'handover' | 'return' | 'restock'
  },
): Promise<number> {
  const api = new Api(page)
  const as = (persona: Persona) => signInAs(page, persona)

  await as('admin')
  const borrowerId = await api.userId('Lea Leiterin')
  const managerId = await api.userId('Mara Matwart')
  await as('borrower')
  let loan = await api.send<LoanDetail>('post', `/api/inventories/${options.inventoryId}/loans`, {
    groupName: 'Stamm Falke',
    eventName: options.title,
    borrowerUserId: borrowerId,
  })
  for (const line of options.lines) {
    loan = await api.send<LoanDetail>('post', `/api/loans/${loan.id}/lines`, line)
  }
  loan = await api.send<LoanDetail>('post', `/api/loans/${loan.id}/actions/request`, {
    pickupOn: isoDay(options.start),
    returnOn: isoDay(options.end),
  })
  if (options.until === 'review') return loan.id

  await as('manager')
  await api.send('patch', `/api/loans/${loan.id}`, { contactUserId: managerId })
  const step = async (action: string, status: string) => {
    loan = await api.send<LoanDetail>('post', `/api/loans/${loan.id}/actions/${action}`, {
      lineIds: idsIn(loan, status),
    })
    loan = await api.send<LoanDetail>('post', `/api/loans/${loan.id}/actions/complete-step`)
  }
  await step('confirm', 'requested')
  if (options.until === 'pack') return loan.id
  await step('pack', 'confirmed')
  if (options.until === 'handover') return loan.id
  await step('pickup', 'packed')
  if (options.until === 'return') return loan.id
  await step('report-return', 'picked_up')
  return loan.id
}
