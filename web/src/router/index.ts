import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

export const router = createRouter({
  history: createWebHistory(),
  // "/hilfe#verleih" from the context help scrolls to the glossary entry.
  scrollBehavior(to, _from, saved) {
    if (saved) return saved
    if (to.hash) return { el: to.hash, top: 16, behavior: 'smooth' }
    return { top: 0 }
  },
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/settings',
      name: 'installation-settings',
      component: () => import('../views/InstallationSettingsView.vue'),
    },
    {
      path: '/diagnose',
      name: 'diagnostics',
      component: () => import('../views/DiagnosticsView.vue'),
    },
    {
      path: '/users',
      name: 'users',
      component: () => import('../views/UsersView.vue'),
    },
    {
      path: '/impressum',
      name: 'impressum',
      component: () => import('../views/ImpressumView.vue'),
    },
    {
      path: '/datenschutz',
      name: 'privacy',
      component: () => import('../views/PrivacyView.vue'),
    },
    {
      path: '/hilfe',
      name: 'help-glossary',
      component: () => import('../views/HelpGlossaryView.vue'),
    },
    {
      path: '/inventories',
      name: 'inventories',
      component: () => import('../views/InventoriesListView.vue'),
    },
    {
      path: '/calendar',
      name: 'calendar',
      component: () => import('../views/CalendarView.vue'),
    },
    {
      path: '/calendar/feeds',
      name: 'calendar-feeds',
      component: () => import('../views/CalendarFeedsView.vue'),
    },
    {
      path: '/my-loans',
      name: 'my-loans',
      component: () => import('../views/MyLoansView.vue'),
    },
    {
      path: '/inventories/:id/material-types',
      name: 'inventory-material-types',
      component: () => import('../views/InventoryMaterialTypesView.vue'),
    },
    {
      path: '/inventories/:id/material',
      name: 'inventory-material',
      component: () => import('../views/InventoryMaterialView.vue'),
    },
    {
      path: '/inventories/:id/pieces',
      redirect: (to) => `/inventories/${to.params.id}/material`,
    },
    {
      path: '/inventories/:id/pieces/:pieceId',
      name: 'piece-detail',
      component: () => import('../views/PieceDetailView.vue'),
    },
    {
      path: '/inventories/:id/stock-lots/:lotId',
      name: 'stock-lot-detail',
      component: () => import('../views/StockLotDetailView.vue'),
    },
    {
      path: '/inventories/:id/stock',
      redirect: (to) => `/inventories/${to.params.id}/material`,
    },
    {
      path: '/inventories/:id/sets',
      name: 'inventory-sets',
      component: () => import('../views/InventorySetsView.vue'),
    },
    {
      path: '/inventories/:id/loans',
      name: 'inventory-loans',
      component: () => import('../views/InventoryLoansView.vue'),
      props: (route) => ({ inventoryId: Number(route.params.id) }),
    },
    {
      path: '/inventories/:id/loans/:loanId',
      name: 'loan-detail',
      component: () => import('../views/LoanDetailView.vue'),
    },
    {
      path: '/inventories/:id/loans/:loanId/mail-preview',
      name: 'loan-mail-preview',
      component: () => import('../views/LoanMailPreviewView.vue'),
    },
    {
      path: '/inventories/:id/sets/:setId',
      name: 'set-detail',
      component: () => import('../views/SetDetailView.vue'),
    },
    {
      path: '/inventories/:id',
      redirect: '/inventories',
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../views/NotFoundView.vue'),
    },
  ],
})
