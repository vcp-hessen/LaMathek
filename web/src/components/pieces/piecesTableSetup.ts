import type { FilterFn } from '@tanstack/vue-table'
import type { MaterialType, Piece } from '../../schemas/material'
import { pieceMatchesVariantFilters } from '../../utils/pieceVariantFilters'
import { variantMapSummary } from '../../utils/variantDisplay'

export const PIECES_PAGE_SIZE_OPTIONS = [25, 50, 100] as const

export type VariantColumnFilterValue = Record<string, string[]>

export function createPieceGlobalFilterFn(
  materialTypes: MaterialType[],
): FilterFn<Piece> {
  const typeById = new Map(materialTypes.map((mt) => [mt.id, mt]))
  return (row, _columnId, filterValue, _addMeta) => {
    const query = String(filterValue ?? '').trim().toLowerCase()
    if (!query) return true
    const piece = row.original
    const mt = typeById.get(piece.materialTypeId)
    const variantText = mt ? variantMapSummary(mt.variants, piece.variant) : ''
    const haystack = [piece.name, piece.materialTypeName, variantText, piece.setName ?? '']
      .join(' ')
      .toLowerCase()
    return haystack.includes(query)
  }
}

export function createMaterialTypeFilterFn(): FilterFn<Piece> {
  return (row, _columnId, filterValue, _addMeta) => {
    const raw = filterValue
    if (raw === '' || raw === undefined || raw === null) return true
    return row.original.materialTypeId === Number(raw)
  }
}

export function createVariantColumnFilterFn(
  materialTypeById: Map<number, MaterialType>,
): FilterFn<Piece> {
  return (row, _columnId, filterValue, _addMeta) => {
    const active = (filterValue ?? {}) as VariantColumnFilterValue
    return pieceMatchesVariantFilters(
      row.original,
      materialTypeById.get(row.original.materialTypeId),
      active,
    )
  }
}
