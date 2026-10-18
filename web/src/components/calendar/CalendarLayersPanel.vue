<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { Inventory } from '../../schemas/inventory'
import CalendarScopeSwitch from './CalendarScopeSwitch.vue'
import type { BorrowerCalendarScope, InventoryCalendarScope } from '../../utils/calendarContent'
import { cycleBorrowerScope, cycleInventoryScope } from '../../utils/calendarContent'

const props = defineProps<{
  borrowerScope: BorrowerCalendarScope
  inventoryScope: Record<number, InventoryCalendarScope>
  inventories: Inventory[]
}>()

const emit = defineEmits<{
  'update:borrowerScope': [value: BorrowerCalendarScope]
  'update:inventoryScope': [inventoryId: number, scope: InventoryCalendarScope]
}>()

const { t } = useI18n()

function setInventoryScope(inventoryId: number, scope: InventoryCalendarScope) {
  emit('update:inventoryScope', inventoryId, scope)
}

function cycleBorrower() {
  emit('update:borrowerScope', cycleBorrowerScope(props.borrowerScope))
}

function cycleInventory(inventory: Inventory) {
  const current = props.inventoryScope[inventory.id] ?? 'off'
  setInventoryScope(inventory.id, cycleInventoryScope(current, inventory.canManage === true))
}
</script>

<template>
  <ul
    class="flex max-h-[min(24rem,70vh)] w-80 max-w-[calc(100vw-1rem)] flex-col gap-0.5 overflow-y-auto p-3"
  >
    <li>
      <div
        role="button"
        tabindex="0"
        class="flex w-full cursor-pointer items-center gap-2 rounded-md px-1 py-1.5 text-left hover:bg-base-200/60"
        @click="cycleBorrower"
        @keydown.enter.prevent="cycleBorrower"
        @keydown.space.prevent="cycleBorrower"
      >
        <CalendarScopeSwitch :model-value="borrowerScope" borrower-only passive />
        <span class="min-w-0 text-sm">{{ t('calendar.contentBorrower') }}</span>
      </div>
    </li>
    <template v-if="inventories.length">
      <li class="divider my-1" role="separator" />
      <li v-for="inventory in inventories" :key="inventory.id">
        <div
          role="button"
          tabindex="0"
          class="flex w-full cursor-pointer items-center gap-2 rounded-md px-1 py-1.5 text-left hover:bg-base-200/60"
          @click="cycleInventory(inventory)"
          @keydown.enter.prevent="cycleInventory(inventory)"
          @keydown.space.prevent="cycleInventory(inventory)"
        >
          <CalendarScopeSwitch
            :model-value="inventoryScope[inventory.id] ?? 'off'"
            :can-manage="inventory.canManage === true"
            passive
          />
          <span class="min-w-0 truncate text-sm font-medium">{{ inventory.name }}</span>
        </div>
      </li>
    </template>
  </ul>
</template>
