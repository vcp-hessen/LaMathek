<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import PiecesPanel from '../components/PiecesPanel.vue'

const route = useRoute()
const inventoryId = computed(() => Number(route.params.id))
</script>

<template>
  <div class="app-page">
    <PiecesPanel
      v-if="Number.isFinite(inventoryId)"
      :key="inventoryId"
      :inventory-id="inventoryId"
    />
  </div>
</template>
