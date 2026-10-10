<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  createInventory,
  deleteInventory,
  fetchInventories,
  fetchInventoryPermissions,
  replaceInventoryPermissions,
  updateInventory,
} from '../api/inventories'
import type { InventoryWritePayload } from '../schemas/inventory'
import { fetchInstallationSettings } from '../api/settings'
import { fetchMe } from '../api/me'
import ExpandableRow from '../components/ExpandableRow.vue'
import SuperuserDestructiveDelete from '../components/SuperuserDestructiveDelete.vue'
import InventoryLocationFields from '../components/InventoryLocationFields.vue'
import InventoryPermissionEditor from '../components/InventoryPermissionEditor.vue'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import type { Inventory } from '../schemas/inventory'
import { useInventoryStore } from '../stores/inventory'

const NEW_ROW = 'new' as const
type ExpandedKey = number | typeof NEW_ROW | null

const { t } = useI18n()
const { messageFor } = useApiErrorMessage()
const inventoryStore = useInventoryStore()
const queryClient = useQueryClient()

const expandedKey = ref<ExpandedKey>(null)
const formError = ref<string | null>(null)

const newName = ref('')
const newAddress = ref('')
const newNotes = ref('')
const newLatitude = ref<number | null>(null)
const newLongitude = ref<number | null>(null)

const editName = ref('')
const editAddress = ref('')
const editNotes = ref('')
const editLatitude = ref<number | null>(null)
const editLongitude = ref<number | null>(null)
const editUserIds = ref<number[]>([])
const permissionsSyncedFor = ref<number | null>(null)

const { data: me } = useQuery({ queryKey: ['me'], queryFn: fetchMe })
const { data: settings } = useQuery({
  queryKey: ['settings'],
  queryFn: fetchInstallationSettings,
})
const { data: inventories, isLoading } = useQuery({
  queryKey: ['inventories'],
  queryFn: fetchInventories,
  enabled: () => !!me.value,
})

const mapDefaults = computed(() => ({
  latitude: settings.value?.mapLatitude ?? 50.65,
  longitude: settings.value?.mapLongitude ?? 9.16,
}))

const editingId = computed(() =>
  typeof expandedKey.value === 'number' ? expandedKey.value : null,
)

const { data: permittedIds } = useQuery({
  queryKey: computed(() => ['inventoryPermissions', editingId.value]),
  queryFn: () => fetchInventoryPermissions(editingId.value!),
  enabled: () => me.value?.isSuperuser === true && editingId.value !== null,
})

watch([editingId, permittedIds], ([id, ids]) => {
  if (id === null || !ids || permissionsSyncedFor.value === id) return
  editUserIds.value = [...ids]
  permissionsSyncedFor.value = id
})

const sortedInventories = computed(() =>
  [...(inventories.value ?? [])].sort((a, b) => a.name.localeCompare(b.name, 'de')),
)

const permissionsReady = computed(
  () => !me.value?.isSuperuser || permissionsSyncedFor.value === editingId.value,
)

function resetCreateDraft() {
  newName.value = ''
  newAddress.value = ''
  newNotes.value = ''
  newLatitude.value = null
  newLongitude.value = null
}

function loadEditDraft(inv: Inventory) {
  editName.value = inv.name
  editAddress.value = inv.address ?? ''
  editNotes.value = inv.notes ?? ''
  editLatitude.value = inv.latitude
  editLongitude.value = inv.longitude
}

function buildPayload(fields: {
  name: string
  address: string
  notes: string
  latitude: number | null
  longitude: number | null
}): InventoryWritePayload {
  return {
    name: fields.name,
    address: fields.address.trim() || null,
    notes: fields.notes.trim() || null,
    latitude: fields.latitude,
    longitude: fields.longitude,
  }
}

function openNewRow() {
  expandedKey.value = NEW_ROW
  resetCreateDraft()
  formError.value = null
}

function closeNewRow() {
  expandedKey.value = null
  formError.value = null
}

function toggleRow(id: number) {
  if (expandedKey.value === id) {
    expandedKey.value = null
    formError.value = null
    return
  }
  permissionsSyncedFor.value = null
  expandedKey.value = id
  const inv = inventories.value?.find((row) => row.id === id)
  if (inv) loadEditDraft(inv)
  formError.value = null
}

function summaryMeta(inv: Inventory): string {
  const parts: string[] = []
  if (inv.address) parts.push(inv.address.split('\n')[0])
  if (inventoryStore.activeInventoryId === inv.id) parts.push(t('inventories.activeTag'))
  return parts.join(' · ')
}

async function refreshInventories() {
  await queryClient.invalidateQueries({ queryKey: ['inventories'] })
}

const createMutation = useMutation({
  mutationFn: () =>
    createInventory(
      buildPayload({
        name: newName.value,
        address: newAddress.value,
        notes: newNotes.value,
        latitude: newLatitude.value,
        longitude: newLongitude.value,
      }),
    ),
  onSuccess: async (created) => {
    expandedKey.value = null
    formError.value = null
    resetCreateDraft()
    inventoryStore.setActiveInventory(created.id)
    await refreshInventories()
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const updateMutation = useMutation({
  mutationFn: (id: number) =>
    updateInventory(
      id,
      buildPayload({
        name: editName.value,
        address: editAddress.value,
        notes: editNotes.value,
        latitude: editLatitude.value,
        longitude: editLongitude.value,
      }),
    ).then(async (inventory) => {
      if (me.value?.isSuperuser) {
        await replaceInventoryPermissions(id, editUserIds.value)
      }
      return inventory
    }),
  onSuccess: async (_data, id) => {
    formError.value = null
    await refreshInventories()
    await queryClient.invalidateQueries({ queryKey: ['inventoryPermissions', id] })
    await queryClient.invalidateQueries({ queryKey: ['inventory', id] })
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const deleteMutation = useMutation({
  mutationFn: (id: number) => deleteInventory(id),
  onSuccess: async (_data, id) => {
    if (expandedKey.value === id) expandedKey.value = null
    formError.value = null
    if (inventoryStore.activeInventoryId === id) {
      inventoryStore.setActiveInventory(null)
    }
    await refreshInventories()
    const remaining = await queryClient.fetchQuery({
      queryKey: ['inventories'],
      queryFn: fetchInventories,
    })
    inventoryStore.reconcileWithAccessible(remaining)
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})
</script>

<template>
  <div class="mx-auto max-w-3xl p-6">
    <div class="card bg-base-100 shadow-md">
      <div class="card-body gap-4 text-left">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="card-title text-lg">{{ t('inventories.title') }}</h2>
          <button
            v-if="me?.isSuperuser && !isLoading"
            type="button"
            class="btn btn-ghost btn-sm"
            :aria-expanded="expandedKey === NEW_ROW"
            @click="openNewRow"
          >
            {{ t('inventories.new') }}
          </button>
        </div>

        <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
        <ul v-else class="list-none">
          <ExpandableRow
            v-if="expandedKey === NEW_ROW"
            :expanded="true"
            @toggle="closeNewRow"
          >
            <template #summary>
              <span class="font-medium">{{ t('inventories.new') }}</span>
            </template>
            <template #editor>
              <form class="inventory-form space-y-4" @submit.prevent="createMutation.mutate()">
                <label class="flex min-w-0 flex-col gap-1">
                  <span class="text-xs opacity-80">{{ t('inventories.nameLabel') }}</span>
                  <input
                    v-model="newName"
                    type="text"
                    class="input input-bordered"
                    required
                  />
                </label>
                <InventoryLocationFields
                  v-model:address="newAddress"
                  v-model:notes="newNotes"
                  v-model:latitude="newLatitude"
                  v-model:longitude="newLongitude"
                  :default-latitude="mapDefaults.latitude"
                  :default-longitude="mapDefaults.longitude"
                />
                <p v-if="formError" class="text-sm text-error">{{ formError }}</p>
                <div class="flex justify-end gap-2">
                  <button type="button" class="btn btn-ghost btn-sm" @click="closeNewRow">
                    {{ t('inventories.cancel') }}
                  </button>
                  <button
                    type="submit"
                    class="btn btn-primary btn-sm"
                    :disabled="createMutation.isPending.value"
                  >
                    {{ t('inventories.create') }}
                  </button>
                </div>
              </form>
            </template>
          </ExpandableRow>

          <ExpandableRow
            v-for="inv in sortedInventories"
            :key="inv.id"
            :expanded="expandedKey === inv.id"
            @toggle="toggleRow(inv.id)"
          >
            <template #summary>
              <div class="flex flex-wrap items-baseline justify-between gap-2">
                <span class="font-medium">{{ inv.name }}</span>
                <span v-if="summaryMeta(inv)" class="text-sm text-base-content/70">
                  {{ summaryMeta(inv) }}
                </span>
              </div>
            </template>
            <template #editor>
              <form
                class="inventory-form space-y-4"
                @submit.prevent="updateMutation.mutate(inv.id)"
              >
                <label class="flex min-w-0 flex-col gap-1">
                  <span class="text-xs opacity-80">{{ t('inventories.nameLabel') }}</span>
                  <input v-model="editName" type="text" class="input input-bordered" required />
                </label>
                <InventoryLocationFields
                  v-model:address="editAddress"
                  v-model:notes="editNotes"
                  v-model:latitude="editLatitude"
                  v-model:longitude="editLongitude"
                  :default-latitude="mapDefaults.latitude"
                  :default-longitude="mapDefaults.longitude"
                />
                <InventoryPermissionEditor
                  v-if="me?.isSuperuser"
                  v-model="editUserIds"
                />
                <p v-if="formError && expandedKey === inv.id" class="text-sm text-error">
                  {{ formError }}
                </p>
                <div class="flex flex-wrap items-center justify-end gap-2">
                  <SuperuserDestructiveDelete
                    v-if="me?.isSuperuser"
                    :warning="t('destructive.inventoryWarning')"
                    :disabled="deleteMutation.isPending.value"
                    @confirmed="deleteMutation.mutate(inv.id)"
                  />
                  <button
                    type="submit"
                    class="btn btn-primary btn-sm"
                    :disabled="updateMutation.isPending.value || !permissionsReady"
                  >
                    {{ t('inventories.rename') }}
                  </button>
                </div>
              </form>
            </template>
          </ExpandableRow>

          <li
            v-if="!sortedInventories.length && expandedKey !== NEW_ROW"
            class="py-2 text-sm opacity-70"
          >
            {{ t('inventories.empty') }}.
            <template v-if="me?.isSuperuser"> {{ t('inventories.emptyHint') }}</template>
            <template v-else> {{ t('inventories.emptyHintUser') }}</template>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
