export type VariantAxis = { label: string; values: string[] }

export function variantAxesSummary(axes: VariantAxis[]): string {
  return axes
    .filter((axis) => axis.values.length > 0)
    .map((axis) => `${axis.label}: ${axis.values.join(', ')}`)
    .join(' · ')
}

export function variantMapSummary(axes: VariantAxis[], map: Record<string, string>): string {
  const parts: string[] = []
  for (const axis of axes) {
    const value = map[axis.label]?.trim()
    if (value) parts.push(value)
  }
  return parts.join(' · ')
}

export function emptyVariantMap(axes: VariantAxis[]): Record<string, string> {
  const map: Record<string, string> = {}
  for (const axis of axes) {
    map[axis.label] = ''
  }
  return map
}

export function syncVariantMapKeys(
  map: Record<string, string>,
  axes: VariantAxis[],
): Record<string, string> {
  const next = emptyVariantMap(axes)
  for (const axis of axes) {
    const existing = map[axis.label]
    if (existing && axis.values.includes(existing)) {
      next[axis.label] = existing
    }
  }
  return next
}
