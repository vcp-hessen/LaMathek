<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { ColumnDef } from '@tanstack/vue-table'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  createInventory,
  deleteInventory,
  fetchInventories,
  fetchInventory,
  fetchInventoryPermissions,
  replaceInventoryPermissions,
  updateInventory,
} from '../api/inventories'
import type { InventoryWritePayload } from '../schemas/inventory'
import { fetchInstallationSettings } from '../api/settings'
import { fetchMe } from '../api/me'
import DataTableFooter from '../components/data-table/DataTableFooter.vue'
import DataTableSearch from '../components/data-table/DataTableSearch.vue'
import { localeSortRow } from '../components/data-table/localeSort'
import SortHeaderButton from '../components/data-table/SortHeaderButton.vue'
import { useClientTable } from '../components/data-table/useClientTable'
import SuperuserDestructiveDelete from '../components/SuperuserDestructiveDelete.vue'
import InventoryLocationFields from '../components/InventoryLocationFields.vue'
import InventoryPermissionEditor from '../components/InventoryPermissionEditor.vue'
import PhotoGallery from '../components/PhotoGallery.vue'
import PhotoThumbnail from '../components/PhotoThumbnail.vue'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import type { Inventory } from '../schemas/inventory'
import { useInventoryStore } from '../stores/inventory'

const { t } = useI18n()
const { messageFor } = useApiErrorMessage()
const inventoryStore = useInventoryStore()
const queryClient = useQueryClient()

const creating = ref(false)
const expandedId = ref<number | null>(null)
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
const savedEdit = ref<{ payload: InventoryWritePayload; userIds: number[] } | null>(null)

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

const editingId = computed(() => expandedId.value)

const { data: permittedUsers } = useQuery({
  queryKey: computed(() => ['inventoryPermissionUsers', editingId.value]),
  queryFn: () => fetchInventoryPermissions(editingId.value!),
  enabled: () => editingId.value !== null,
})

const { data: editingInventory } = useQuery({
  queryKey: computed(() => ['inventory', editingId.value]),
  queryFn: () => fetchInventory(editingId.value!),
  enabled: () => editingId.value !== null,
})

async function refreshInventoryPhotos() {
  if (editingId.value === null) return
  await queryClient.invalidateQueries({ queryKey: ['inventory', editingId.value] })
  await queryClient.invalidateQueries({ queryKey: ['inventories'] })
}

function sortedIds(ids: number[]) {
  return [...ids].sort((a, b) => a - b)
}

function currentInventoryEdit() {
  return {
    payload: buildPayload({
      name: editName.value,
      address: editAddress.value,
      notes: editNotes.value,
      latitude: editLatitude.value,
      longitude: editLongitude.value,
    }),
    userIds: sortedIds(editUserIds.value),
  }
}

const editDirty = computed(
  () =>
    savedEdit.value !== null &&
    JSON.stringify(currentInventoryEdit()) !== JSON.stringify(savedEdit.value),
)

watch([editingId, permittedUsers], ([id, users]) => {
  if (id === null || !users || permissionsSyncedFor.value === id) return
  editUserIds.value = users.map((user) => user.id)
  permissionsSyncedFor.value = id
  if (savedEdit.value) {
    savedEdit.value = { ...savedEdit.value, userIds: sortedIds(editUserIds.value) }
  }
})

const columns = computed<ColumnDef<Inventory>[]>(() => [
  {
    id: 'name',
    accessorFn: (inv) => inv.name,
    sortingFn: localeSortRow,
  },
  {
    id: 'address',
    accessorFn: (inv) => inv.address?.split('\n')[0] ?? '',
    sortingFn: localeSortRow,
  },
  {
    id: 'active',
    accessorFn: (inv) =>
      inventoryStore.activeInventoryId === inv.id ? t('inventories.activeTag') : '',
    sortingFn: localeSortRow,
  },
])

const {
  table,
  globalFilter,
  sorting,
  pagination,
  tableRows,
  filteredCount,
  pageCount,
  currentPage,
  pageFrom,
  pageTo,
  goToPage,
  setPageSize,
} = useClientTable<Inventory>({
  data: () => inventories.value ?? [],
  columns,
  getRowId: (inv) => String(inv.id),
  globalFilterFn: () => (row, _columnId, filterValue) => {
    const query = String(filterValue ?? '').trim().toLowerCase()
    if (!query) return true
    const inv = row.original
    const haystack = [inv.name, inv.address ?? '', inv.notes ?? ''].join(' ').toLowerCase()
    return haystack.includes(query)
  },
  initialSorting: [{ id: 'name', desc: false }],
})

watch(
  [globalFilter, sorting, () => pagination.value.pageIndex, () => pagination.value.pageSize],
  () => {
    expandedId.value = null
  },
)

const permissionsReady = computed(
  () => permissionsSyncedFor.value === editingId.value,
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
  savedEdit.value = {
    payload: buildPayload({
      name: inv.name,
      address: inv.address ?? '',
      notes: inv.notes ?? '',
      latitude: inv.latitude,
      longitude: inv.longitude,
    }),
    userIds: [],
  }
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
  creating.value = true
  expandedId.value = null
  resetCreateDraft()
  formError.value = null
}

function closeNewRow() {
  creating.value = false
  formError.value = null
}

function toggleRow(id: number) {
  if (expandedId.value === id) {
    expandedId.value = null
    formError.value = null
    return
  }
  creating.value = false
  permissionsSyncedFor.value = null
  expandedId.value = id
  const inv = inventories.value?.find((row) => row.id === id)
  if (inv) loadEditDraft(inv)
  formError.value = null
}

function sortedState(columnId: string): false | 'asc' | 'desc' {
  return table.getColumn(columnId)?.getIsSorted() ?? false
}

function onRowKeydown(event: KeyboardEvent, id: number) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    toggleRow(id)
  }
}

function addressLine(inv: Inventory): string {
  return inv.address?.split('\n')[0] ?? ''
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
    creating.value = false
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
      await replaceInventoryPermissions(id, editUserIds.value)
      return inventory
    }),
  onSuccess: async (_data, id) => {
    formError.value = null
    savedEdit.value = currentInventoryEdit()
    await refreshInventories()
    await queryClient.invalidateQueries({ queryKey: ['inventoryPermissionUsers', id] })
    await queryClient.invalidateQueries({ queryKey: ['inventory', id] })
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const deleteMutation = useMutation({
  mutationFn: (id: number) => deleteInventory(id),
  onSuccess: async (_data, id) => {
    if (expandedId.value === id) expandedId.value = null
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
  <div class="app-page gap-4">
        <div class="app-section-header flex flex-wrap items-center justify-between gap-2">
          <h2 class="app-page-title">{{ t('inventories.title') }}</h2>
          <button
            v-if="me?.isSuperuser && !isLoading"
            type="button"
            class="btn btn-ghost btn-sm"
            :aria-expanded="creating"
            @click="creating ? closeNewRow() : openNewRow()"
          >
            {{ t('inventories.new') }}
          </button>
        </div>

        <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
        <template v-else>
          <form
            v-if="creating"
            class="inventory-form space-y-4 rounded-lg border border-base-200 p-4"
            @submit.prevent="createMutation.mutate()"
          >
            <p class="text-sm font-medium">{{ t('inventories.new') }}</p>
            <label class="flex min-w-0 flex-col gap-1">
              <span class="text-xs opacity-80">{{ t('inventories.nameLabel') }}</span>
              <input v-model="newName" type="text" class="input input-bordered" required />
            </label>
            <InventoryLocationFields
              v-model:address="newAddress"
              v-model:notes="newNotes"
              v-model:latitude="newLatitude"
              v-model:longitude="newLongitude"
              :default-latitude="mapDefaults.latitude"
              :default-longitude="mapDefaults.longitude"
            />
            <p v-if="formError && expandedId === null" class="text-sm text-error">{{ formError }}</p>
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

          <p v-if="!(inventories?.length)" class="text-sm opacity-70">
            {{ t('inventories.empty') }}.
            <template v-if="me?.isSuperuser"> {{ t('inventories.emptyHint') }}</template>
            <template v-else> {{ t('inventories.emptyHintUser') }}</template>
          </p>
          <div v-else class="rounded-lg border border-base-200">
            <div
              class="data-table-toolbar flex flex-col gap-3 border-b border-base-200 p-3 sm:flex-row sm:flex-wrap sm:items-end"
            >
              <DataTableSearch
                :model-value="globalFilter"
                :label="t('inventories.searchLabel')"
                :placeholder="t('inventories.searchPlaceholder')"
                @update:model-value="globalFilter = $event"
              />
            </div>
            <div class="overflow-x-auto">
              <table class="table table-sm data-table">
                <thead>
                  <tr>
                    <th class="data-table-col-photo hidden sm:table-cell">
                      <span class="sr-only">{{ t('dataTable.photo') }}</span>
                    </th>
                    <th class="data-table-col-lead">
                      <SortHeaderButton
                        :label="t('inventories.columnName')"
                        :sorted="sortedState('name')"
                        @toggle="table.getColumn('name')?.toggleSorting()"
                      />
                    </th>
                    <th class="hidden md:table-cell">
                      <SortHeaderButton
                        :label="t('inventories.addressLabel')"
                        :sorted="sortedState('address')"
                        @toggle="table.getColumn('address')?.toggleSorting()"
                      />
                    </th>
                    <th class="hidden sm:table-cell">
                      <SortHeaderButton
                        :label="t('inventories.columnStatus')"
                        :sorted="sortedState('active')"
                        @toggle="table.getColumn('active')?.toggleSorting()"
                      />
                    </th>
                  </tr>
                </thead>
                <tbody v-if="tableRows.length === 0">
                  <tr>
                    <td colspan="4" class="py-8 text-center text-sm opacity-70">
                      {{ t('dataTable.noResults') }}
                    </td>
                  </tr>
                </tbody>
                <tbody v-for="(row, index) in tableRows" v-else :key="row.id">
                  <tr
                    tabindex="0"
                    role="button"
                    class="data-table-row cursor-pointer"
                    :class="{ 'data-table-row--stripe': index % 2 === 1 }"
                    :aria-expanded="expandedId === row.original.id"
                    @click="toggleRow(row.original.id)"
                    @keydown="onRowKeydown($event, row.original.id)"
                  >
                    <td class="data-table-col-photo hidden sm:table-cell">
                      <PhotoThumbnail :photo-id="row.original.coverPhotoId" />
                    </td>
                    <td class="data-table-col-lead min-w-0">
                      <div class="flex items-start gap-2">
                        <span
                          class="mt-0.5 shrink-0 text-base-content/50 transition-transform duration-200"
                          :class="{ 'rotate-90': expandedId === row.original.id }"
                          aria-hidden="true"
                        >
                          ›
                        </span>
                        <div class="min-w-0">
                          <span class="font-medium">{{ row.original.name }}</span>
                          <div class="mt-0.5 space-y-0.5 text-xs opacity-70">
                            <span v-if="addressLine(row.original)" class="block md:hidden">
                              {{ addressLine(row.original) }}
                            </span>
                            <span
                              v-if="inventoryStore.activeInventoryId === row.original.id"
                              class="block sm:hidden"
                            >
                              {{ t('inventories.activeTag') }}
                            </span>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td class="hidden max-w-[16rem] truncate md:table-cell">
                      {{ addressLine(row.original) || '—' }}
                    </td>
                    <td class="hidden sm:table-cell">
                      <span v-if="inventoryStore.activeInventoryId === row.original.id">
                        {{ t('inventories.activeTag') }}
                      </span>
                      <span v-else>—</span>
                    </td>
                  </tr>
                  <tr v-if="expandedId === row.original.id" class="data-table-editor">
                    <td colspan="4" class="pb-4 pt-3">
                      <form
                        class="inventory-form space-y-4 pl-5"
                        @submit.prevent="updateMutation.mutate(row.original.id)"
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
                          v-if="editingId === row.original.id"
                          v-model="editUserIds"
                          :inventory-id="row.original.id"
                        />
                        <div v-if="editingId === row.original.id && editingInventory">
                          <h3 class="mb-2 text-sm font-semibold">{{ t('photos.heading') }}</h3>
                          <PhotoGallery
                            :owner="{ kind: 'inventory', inventoryId: row.original.id }"
                            :photos="editingInventory.photos ?? []"
                            @change="refreshInventoryPhotos"
                          />
                        </div>
                        <p v-if="formError && expandedId === row.original.id" class="text-sm text-error">
                          {{ formError }}
                        </p>
                        <div class="flex flex-wrap items-center justify-end gap-2">
                          <SuperuserDestructiveDelete
                            v-if="me?.isSuperuser"
                            :warning="t('destructive.inventoryWarning')"
                            :disabled="deleteMutation.isPending.value"
                            @confirmed="deleteMutation.mutate(row.original.id)"
                          />
                          <button
                            type="submit"
                            class="btn btn-primary btn-sm"
                            :disabled="updateMutation.isPending.value || !permissionsReady || !editDirty"
                          >
                            {{ t('inventories.rename') }}
                          </button>
                        </div>
                      </form>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <DataTableFooter
              :page-from="pageFrom"
              :page-to="pageTo"
              :total="filteredCount"
              :current-page="currentPage"
              :page-count="pageCount"
              :page-size="pagination.pageSize"
              @update:page-size="setPageSize"
              @go-to-page="goToPage"
            />
          </div>
        </template>
  </div>
</template>
