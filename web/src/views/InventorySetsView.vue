<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SetsPanel from '../components/SetsPanel.vue'
import { useInventoryCanManage } from '../composables/useInventoryCanManage'

const route = useRoute()
const inventoryId = computed(() => Number(route.params.id))
const { canManage } = useInventoryCanManage(inventoryId)
</script>

<template>
  <div class="app-page">
    <SetsPanel
      v-if="Number.isFinite(inventoryId)"
      :key="inventoryId"
      :inventory-id="inventoryId"
      :can-manage="canManage"
    />
  </div>
</template>
