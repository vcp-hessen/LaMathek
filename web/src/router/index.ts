import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import InventoriesListView from '../views/InventoriesListView.vue'
import InventoryDetailView from '../views/InventoryDetailView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/inventories',
      name: 'inventories',
      component: InventoriesListView,
    },
    {
      path: '/inventories/:id',
      name: 'inventory-detail',
      component: InventoryDetailView,
    },
  ],
})
