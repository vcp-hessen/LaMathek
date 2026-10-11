import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchInventories } from '../api/inventories'
import { fetchPiece } from '../api/material'
import { fetchLoan } from '../api/loans'
import { fetchSet } from '../api/sets'
import { fetchMe } from '../api/me'

export type BreadcrumbItem = {
  label: string
  to?: string
}

const sectionLabelByRoute: Record<string, string> = {
  'inventory-material-types': 'nav.materialTypes',
  'inventory-pieces': 'nav.pieces',
  'inventory-stock': 'nav.stock',
  'inventory-sets': 'nav.sets',
  'inventory-loans': 'nav.loans',
}

export function useAppBreadcrumbs() {
  const route = useRoute()
  const { t } = useI18n()

  const { data: me } = useQuery({ queryKey: ['me'], queryFn: fetchMe })

  const { data: inventories } = useQuery({
    queryKey: ['inventories'],
    queryFn: fetchInventories,
    enabled: () => !!me.value,
  })

  const routeInventoryId = computed(() => {
    const raw = route.params.id
    if (raw === undefined || raw === '') return null
    const id = Number(raw)
    return Number.isFinite(id) ? id : null
  })

  const routeSetId = computed(() => {
    if (route.name !== 'set-detail') return null
    const id = Number(route.params.setId)
    return Number.isFinite(id) ? id : null
  })

  const routeLoanId = computed(() => {
    if (route.name !== 'loan-detail') return null
    const id = Number(route.params.loanId)
    return Number.isFinite(id) ? id : null
  })

  const routePieceId = computed(() => {
    if (route.name !== 'piece-detail') return null
    const id = Number(route.params.pieceId)
    return Number.isFinite(id) ? id : null
  })

  const { data: setDetail } = useQuery({
    queryKey: computed(() => ['set', routeSetId.value]),
    queryFn: () => fetchSet(routeSetId.value!),
    enabled: () => routeSetId.value !== null,
  })

  const { data: loanDetail } = useQuery({
    queryKey: computed(() => ['loan', routeLoanId.value]),
    queryFn: () => fetchLoan(routeLoanId.value!),
    enabled: () => routeLoanId.value !== null,
  })

  const { data: pieceDetail } = useQuery({
    queryKey: computed(() => ['piece', routePieceId.value]),
    queryFn: () => fetchPiece(routePieceId.value!),
    enabled: () => routePieceId.value !== null,
  })

  function inventoryLabel(id: number): string {
    return inventories.value?.find((i) => i.id === id)?.name ?? t('inventories.detail')
  }

  function inventoryTrail(id: number): BreadcrumbItem[] {
    return [{ label: inventoryLabel(id), to: `/inventories/${id}/material-types` }]
  }

  const items = computed((): BreadcrumbItem[] => {
    switch (route.name) {
      case 'home':
        return []
      case 'installation-settings':
        return [{ label: t('settings.heading') }]
      case 'users':
        return [{ label: t('users.heading') }]
      case 'impressum':
        return [{ label: t('impressum.heading') }]
      case 'privacy':
        return [{ label: t('privacy.heading') }]
      case 'inventories':
        return [{ label: t('inventories.title') }]
      case 'inventory-material-types':
      case 'inventory-pieces':
      case 'inventory-stock':
      case 'inventory-sets':
      case 'inventory-loans': {
        const id = routeInventoryId.value
        const sectionKey = sectionLabelByRoute[String(route.name)]
        if (id === null || !sectionKey) return []
        return [...inventoryTrail(id), { label: t(sectionKey) }]
      }
      case 'set-detail': {
        const id = routeInventoryId.value
        const setName = setDetail.value?.name ?? t('sets.heading')
        if (id === null) return [{ label: setName }]
        return [
          ...inventoryTrail(id),
          { label: t('nav.sets'), to: `/inventories/${id}/sets` },
          { label: setName },
        ]
      }
      case 'loan-detail': {
        const id = routeInventoryId.value
        const label =
          loanDetail.value?.groupName ??
          `${t('loans.heading')} ${routeLoanId.value ?? ''}`
        if (id === null) return [{ label }]
        return [
          ...inventoryTrail(id),
          { label: t('nav.loans'), to: `/inventories/${id}/loans` },
          { label },
        ]
      }
      case 'piece-detail': {
        const id = routeInventoryId.value
        const label = pieceDetail.value?.name ?? t('material.piecesHeading')
        if (id === null) return [{ label }]
        return [
          ...inventoryTrail(id),
          { label: t('nav.pieces'), to: `/inventories/${id}/pieces` },
          { label },
        ]
      }
      default:
        return []
    }
  })

  return { items }
}
