<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MaterialPanel from '../components/MaterialPanel.vue'

const route = useRoute()
const inventoryId = computed(() => Number(route.params.id))
</script>

<template>
  <div class="app-page">
    <MaterialPanel
      v-if="Number.isFinite(inventoryId)"
      :key="inventoryId"
      :inventory-id="inventoryId"
    />
  </div>
</template>
