import type { MaterialType, Piece } from '../schemas/material'

export type VariantAxisCatalogEntry = { label: string; values: string[] }

export function buildVariantAxisCatalog(materialTypes: MaterialType[]): VariantAxisCatalogEntry[] {
  const byLabel = new Map<string, Set<string>>()
  for (const mt of materialTypes) {
    for (const axis of mt.variants) {
      const label = axis.label.trim()
      if (!label) continue
      const bucket = byLabel.get(label) ?? new Set<string>()
      for (const value of axis.values) {
        const trimmed = value.trim()
        if (trimmed) bucket.add(trimmed)
      }
      if (bucket.size > 0) byLabel.set(label, bucket)
    }
  }
  return [...byLabel.entries()]
    .map(([label, values]) => ({
      label,
      values: [...values].sort((a, b) => a.localeCompare(b, 'de')),
    }))
    .sort((a, b) => a.label.localeCompare(b.label, 'de'))
}

export function variantFiltersAreActive(activeFilters: Record<string, string[]>): boolean {
  return Object.values(activeFilters).some((values) => values.length > 0)
}

/** Drops axes and values that are not defined on the given catalog (e.g. after material-type filter). */
export function pruneVariantFilterToCatalog(
  activeFilters: Record<string, string[]>,
  catalog: VariantAxisCatalogEntry[],
): Record<string, string[]> {
  const catalogByLabel = new Map(catalog.map((entry) => [entry.label, new Set(entry.values)]))
  const next: Record<string, string[]> = {}
  for (const [label, values] of Object.entries(activeFilters)) {
    const allowed = catalogByLabel.get(label)
    if (!allowed) continue
    next[label] = values.filter((value) => allowed.has(value))
  }
  return next
}

export function pieceMatchesVariantFilters(
  piece: Piece,
  materialType: MaterialType | undefined,
  activeFilters: Record<string, string[]>,
): boolean {
  const active = Object.entries(activeFilters).filter(([, values]) => values.length > 0)
  if (!active.length) return true
  if (!materialType) return false

  for (const [axisLabel, selectedValues] of active) {
    const hasAxis = materialType.variants.some((axis) => axis.label === axisLabel)
    if (!hasAxis) return false
    const pieceValue = piece.variant[axisLabel]?.trim()
    if (!pieceValue) return false
    if (!selectedValues.includes(pieceValue)) return false
  }
  return true
}
