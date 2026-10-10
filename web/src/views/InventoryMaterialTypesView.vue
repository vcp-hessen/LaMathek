<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MaterialTypesPanel from '../components/MaterialTypesPanel.vue'

const route = useRoute()
const inventoryId = computed(() => Number(route.params.id))
</script>

<template>
  <div class="app-page">
    <MaterialTypesPanel
      v-if="Number.isFinite(inventoryId)"
      :key="inventoryId"
      :inventory-id="inventoryId"
    />
  </div>
</template>
