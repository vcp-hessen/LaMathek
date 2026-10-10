<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SetsPanel from '../components/SetsPanel.vue'

const route = useRoute()
const inventoryId = computed(() => Number(route.params.id))
</script>

<template>
  <div class="mx-auto max-w-3xl p-6">
    <SetsPanel
      v-if="Number.isFinite(inventoryId)"
      :key="inventoryId"
      :inventory-id="inventoryId"
    />
  </div>
</template>
