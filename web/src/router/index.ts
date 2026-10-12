import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import ImpressumView from '../views/ImpressumView.vue'
import PrivacyView from '../views/PrivacyView.vue'
import InventoriesListView from '../views/InventoriesListView.vue'
import InstallationSettingsView from '../views/InstallationSettingsView.vue'
import DiagnosticsView from '../views/DiagnosticsView.vue'
import UsersView from '../views/UsersView.vue'
import InventoryMaterialTypesView from '../views/InventoryMaterialTypesView.vue'
import InventoryMaterialView from '../views/InventoryMaterialView.vue'
import PieceDetailView from '../views/PieceDetailView.vue'
import StockLotDetailView from '../views/StockLotDetailView.vue'
import InventoryLoansView from '../views/InventoryLoansView.vue'
import InventorySetsView from '../views/InventorySetsView.vue'
import LoanDetailView from '../views/LoanDetailView.vue'
import SetDetailView from '../views/SetDetailView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/settings',
      name: 'installation-settings',
      component: InstallationSettingsView,
    },
    {
      path: '/diagnose',
      name: 'diagnostics',
      component: DiagnosticsView,
    },
    {
      path: '/users',
      name: 'users',
      component: UsersView,
    },
    {
      path: '/impressum',
      name: 'impressum',
      component: ImpressumView,
    },
    {
      path: '/datenschutz',
      name: 'privacy',
      component: PrivacyView,
    },
    {
      path: '/inventories',
      name: 'inventories',
      component: InventoriesListView,
    },
    {
      path: '/inventories/:id/material-types',
      name: 'inventory-material-types',
      component: InventoryMaterialTypesView,
    },
    {
      path: '/inventories/:id/material',
      name: 'inventory-material',
      component: InventoryMaterialView,
    },
    {
      path: '/inventories/:id/pieces',
      redirect: (to) => `/inventories/${to.params.id}/material`,
    },
    {
      path: '/inventories/:id/pieces/:pieceId',
      name: 'piece-detail',
      component: PieceDetailView,
    },
    {
      path: '/inventories/:id/stock-lots/:lotId',
      name: 'stock-lot-detail',
      component: StockLotDetailView,
    },
    {
      path: '/inventories/:id/stock',
      redirect: (to) => `/inventories/${to.params.id}/material`,
    },
    {
      path: '/inventories/:id/sets',
      name: 'inventory-sets',
      component: InventorySetsView,
    },
    {
      path: '/inventories/:id/loans',
      name: 'inventory-loans',
      component: InventoryLoansView,
      props: (route) => ({ inventoryId: Number(route.params.id) }),
    },
    {
      path: '/inventories/:id/loans/:loanId',
      name: 'loan-detail',
      component: LoanDetailView,
    },
    {
      path: '/inventories/:id/sets/:setId',
      name: 'set-detail',
      component: SetDetailView,
    },
    {
      path: '/inventories/:id',
      redirect: '/inventories',
    },
  ],
})
