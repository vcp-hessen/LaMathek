/** Route names where an inventory workspace context applies (incl. active box picker). */
export const INVENTORY_WORKSPACE_ROUTE_NAMES = new Set([
  'inventory-material-types',
  'inventory-material',
  'piece-detail',
  'stock-lot-detail',
  'inventory-sets',
  'set-detail',
  'inventory-loans',
  'loan-detail',
])

export function isInventoryWorkspaceRoute(name: string | symbol | null | undefined): boolean {
  if (!name) return false
  return INVENTORY_WORKSPACE_ROUTE_NAMES.has(String(name))
}
