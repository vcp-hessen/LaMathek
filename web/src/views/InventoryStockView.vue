<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import StockPanel from '../components/StockPanel.vue'

const route = useRoute()
const inventoryId = computed(() => Number(route.params.id))
</script>

<template>
  <div class="mx-auto max-w-3xl p-6">
    <StockPanel
      v-if="Number.isFinite(inventoryId)"
      :key="inventoryId"
      :inventory-id="inventoryId"
    />
  </div>
</template>
