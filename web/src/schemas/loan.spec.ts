import { describe, expect, it } from 'vitest'

import { loanSchema } from './loan'

// Real API payload (GET /api/inventories/1/loans) of a fresh box without a Gruppe.
const draftWithoutGroup = {
  borrowerPhone: '',
  borrowerUserId: 1,
  borrowerUserName: 'Dev User',
  contactPhone: null,
  contactUserId: null,
  contactUserName: null,
  coverPhotoId: null,
  eventId: null,
  eventName: null,
  groupId: null,
  groupName: '',
  id: 8,
  inventoryId: 1,
  inventoryName: 'Landesmaterial Donnerskopf',
  kind: 'short',
  phase: 'draft',
  pickupNote: '',
  pickupOn: null,
  returnNote: '',
  returnOn: null,
  wishPickupOn: null,
  wishReturnOn: null,
}

describe('loanSchema', () => {
  it('accepts a draft without a Gruppe (D0003)', () => {
    const result = loanSchema.safeParse(draftWithoutGroup)
    expect(result.success, JSON.stringify(result.error?.issues)).toBe(true)
  })
})
