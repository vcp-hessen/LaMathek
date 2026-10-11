import type { FilterFn } from '@tanstack/vue-table'
import type { MaterialType, Piece, StockLot, StockRow, VariantAxis } from '../../schemas/material'
import { pieceMatchesVariantFilters } from '../../utils/pieceVariantFilters'
import { variantMapSummary } from '../../utils/variantDisplay'
import { PIECES_PAGE_SIZE_OPTIONS } from '../pieces/piecesTableSetup'

export const MATERIAL_PAGE_SIZE_OPTIONS = PIECES_PAGE_SIZE_OPTIONS

export type VariantColumnFilterValue = Record<string, string[]>

export type StockLotListItem = StockLot & {
  materialTypeId: number
  materialTypeName: string
  unit: string | null
  variants: VariantAxis[]
}

export type MaterialRow =
  | { kind: 'piece'; id: string; piece: Piece }
  | { kind: 'stockLot'; id: string; lot: StockLotListItem }

export function stockLotListItemFromStocks(
  stocks: StockRow[],
  lotId: number,
): StockLotListItem | null {
  for (const row of stocks) {
    for (const lot of row.lots) {
      if (lot.id === lotId) {
        return {
          ...lot,
          materialTypeId: row.materialTypeId,
          materialTypeName: row.materialTypeName,
          unit: row.unit,
          variants: row.variants,
        }
      }
    }
  }
  return null
}

export function materialRowsFromPiecesAndLots(
  pieces: Piece[],
  lots: StockLotListItem[],
): MaterialRow[] {
  const pieceRows: MaterialRow[] = pieces.map((piece) => ({
    kind: 'piece',
    id: `piece-${piece.id}`,
    piece,
  }))
  const lotRows: MaterialRow[] = lots.map((lot) => ({
    kind: 'stockLot',
    id: `lot-${lot.id}`,
    lot,
  }))
  return [...pieceRows, ...lotRows]
}

export function rowDisplayName(row: MaterialRow, unlabeledLotLabel: string): string {
  if (row.kind === 'piece') return row.piece.name
  const label = row.lot.label?.trim()
  return label || unlabeledLotLabel
}

export function rowMaterialTypeId(row: MaterialRow): number {
  return row.kind === 'piece' ? row.piece.materialTypeId : row.lot.materialTypeId
}

export function rowMaterialTypeName(row: MaterialRow): string {
  return row.kind === 'piece' ? row.piece.materialTypeName : row.lot.materialTypeName
}

export function rowCoverPhotoId(row: MaterialRow): number | null | undefined {
  return row.kind === 'piece' ? row.piece.coverPhotoId : row.lot.coverPhotoId
}

function stockLotMatchesVariantFilters(
  lot: StockLotListItem,
  materialType: MaterialType | undefined,
  activeFilters: Record<string, string[]>,
): boolean {
  const active = Object.entries(activeFilters).filter(([, values]) => values.length > 0)
  if (!active.length) return true
  if (!materialType) return false

  for (const [axisLabel, selectedValues] of active) {
    const hasAxis = materialType.variants.some((axis) => axis.label === axisLabel)
    if (!hasAxis) return false
    const lotValue = lot.variant[axisLabel]?.trim()
    if (!lotValue) return false
    if (!selectedValues.includes(lotValue)) return false
  }
  return true
}

export function createMaterialGlobalFilterFn(
  materialTypes: MaterialType[],
  unlabeledLotLabel: string,
): FilterFn<MaterialRow> {
  const typeById = new Map(materialTypes.map((mt) => [mt.id, mt]))
  return (row, _columnId, filterValue, _addMeta) => {
    const query = String(filterValue ?? '').trim().toLowerCase()
    if (!query) return true
    const original = row.original
    if (original.kind === 'piece') {
      const piece = original.piece
      const mt = typeById.get(piece.materialTypeId)
      const variantText = mt ? variantMapSummary(mt.variants, piece.variant) : ''
      const haystack = [piece.name, piece.materialTypeName, variantText, piece.setName ?? '']
        .join(' ')
        .toLowerCase()
      return haystack.includes(query)
    }
    const lot = original.lot
    const variantText = variantMapSummary(lot.variants, lot.variant)
    const displayName = rowDisplayName(original, unlabeledLotLabel)
    const qty = `${lot.quantity}${lot.unit ? ` ${lot.unit}` : ''}`
    const haystack = [displayName, lot.materialTypeName, variantText, qty].join(' ').toLowerCase()
    return haystack.includes(query)
  }
}

export function createMaterialTypeFilterFn(): FilterFn<MaterialRow> {
  return (row, _columnId, filterValue, _addMeta) => {
    const raw = filterValue
    if (raw === '' || raw === undefined || raw === null) return true
    return rowMaterialTypeId(row.original) === Number(raw)
  }
}

export function createMaterialVariantColumnFilterFn(
  materialTypeById: Map<number, MaterialType>,
): FilterFn<MaterialRow> {
  return (row, _columnId, filterValue, _addMeta) => {
    const active = (filterValue ?? {}) as VariantColumnFilterValue
    const original = row.original
    const mt = materialTypeById.get(rowMaterialTypeId(original))
    if (original.kind === 'piece') {
      return pieceMatchesVariantFilters(original.piece, mt, active)
    }
    return stockLotMatchesVariantFilters(original.lot, mt, active)
  }
}
