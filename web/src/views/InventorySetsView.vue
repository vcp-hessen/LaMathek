<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SetsPanel from '../components/SetsPanel.vue'

const route = useRoute()
const inventoryId = computed(() => Number(route.params.id))
</script>

<template>
  <div class="app-page">
    <SetsPanel
      v-if="Number.isFinite(inventoryId)"
      :key="inventoryId"
      :inventory-id="inventoryId"
    />
  </div>
</template>
