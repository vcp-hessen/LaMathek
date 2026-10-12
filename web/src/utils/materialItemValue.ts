import type { MaterialItemStatus, Piece, StockLot } from '../schemas/material'

/** Parse user-entered euro amount (e.g. "199,99") to integer cents, or null if empty. */
export function euroInputToCents(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  const normalized = trimmed.replace(/\s/g, '').replace(',', '.')
  const amount = Number(normalized)
  if (!Number.isFinite(amount) || amount < 0) {
    throw new Error('invalid_new_value')
  }
  return Math.round(amount * 100)
}

export function centsToEuroInput(cents: number | null | undefined): string {
  if (cents == null) return ''
  return (cents / 100).toFixed(2).replace('.', ',')
}

export type ItemMetadataDraft = {
  acquiredYear: number | ''
  note: string
  source: string
  serialNumber: string
  newValueEuro: string
  status: MaterialItemStatus
}

export function emptyItemMetadataDraft(): ItemMetadataDraft {
  return {
    acquiredYear: '',
    note: '',
    source: '',
    serialNumber: '',
    newValueEuro: '',
    status: 'active',
  }
}

export function itemMetadataFromRecord(item: Piece | StockLot): ItemMetadataDraft {
  return {
    acquiredYear: item.acquiredYear ?? '',
    note: item.note ?? '',
    source: item.source ?? '',
    serialNumber: item.serialNumber ?? '',
    newValueEuro: centsToEuroInput(item.newValueCents),
    status: item.status,
  }
}

export function itemMetadataToWritePayload(
  draft: ItemMetadataDraft,
  options?: { includeStatus?: boolean; create?: boolean },
): Record<string, unknown> {
  const payload: Record<string, unknown> = {}
  const year = draft.acquiredYear === '' ? null : draft.acquiredYear
  const note = draft.note.trim() || null
  const source = draft.source.trim() || null
  const serialNumber = draft.serialNumber.trim() || null
  let newValueCents: number | null = null
  if (draft.newValueEuro.trim()) {
    newValueCents = euroInputToCents(draft.newValueEuro)
  }

  if (options?.create) {
    if (year !== null) payload.acquiredYear = year
    if (note) payload.note = note
    if (source) payload.source = source
    if (serialNumber) payload.serialNumber = serialNumber
    if (newValueCents !== null) payload.newValueCents = newValueCents
    return payload
  }

  payload.acquiredYear = year
  payload.note = note
  payload.source = source
  payload.serialNumber = serialNumber
  payload.newValueCents = newValueCents
  if (options?.includeStatus) payload.status = draft.status
  return payload
}
