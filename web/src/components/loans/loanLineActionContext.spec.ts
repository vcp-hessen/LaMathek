import { describe, expect, it } from 'vitest'

import type { LoanLine } from '../../schemas/loan'
import { deriveLineActionContext } from './loanLineActionContext'

function line(id: number, status: LoanLine['status']): LoanLine {
  return {
    kind: 'piece',
    id,
    status,
    note: '',
    reason: '',
    replacesLineId: null,
    splitFromLineId: null,
    requestNotified: true,
    returnedQuantity: null,
    statusBeforeEnd: null,
    warnings: [],
    originSetId: null,
    originSetName: null,
    originSetRole: null,
    pieceId: id,
    pieceName: `DV ${id}`,
    materialTypeName: 'Doppelviereckplane',
  }
}

describe('deriveLineActionContext', () => {
  it('offers Rückgabe melden in the return step', () => {
    const context = deriveLineActionContext([line(1, 'picked_up'), line(2, 'picked_up')], 'return')
    expect(context).toMatchObject({ kind: 'return', pickedUpCount: 2, restockCount: 0, lossCount: 2 })
  })

  it('offers Übernehmen and Verlust in the restock step (found by the e2e journey)', () => {
    const context = deriveLineActionContext([line(1, 'return_reported'), line(2, 'return_reported')], 'restock')
    expect(context).toMatchObject({ kind: 'return', pickedUpCount: 0, restockCount: 2, lossCount: 2 })
  })

  it('names the wrong step when the gates allow nothing here', () => {
    expect(deriveLineActionContext([line(1, 'return_reported')], 'pack')).toEqual({
      kind: 'hint',
      hint: 'wrong_step',
    })
  })
})
