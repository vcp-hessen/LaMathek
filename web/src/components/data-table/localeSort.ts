import type { Row } from '@tanstack/vue-table'

export function localeSortRow<T>(rowA: Row<T>, rowB: Row<T>, columnId: string) {
  return String(rowA.getValue(columnId)).localeCompare(String(rowB.getValue(columnId)), 'de')
}
