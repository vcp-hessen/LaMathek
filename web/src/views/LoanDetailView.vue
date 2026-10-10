<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchMaterialTypes, fetchPieces } from '../api/material'
import {
  addLoanPieceLine,
  addLoanSetAssignmentLines,
  addLoanSetOptionalLines,
  addLoanStockLine,
  fetchLoan,
  handOutLoan,
  recordLoanReturn,
  removeLoanLine,
} from '../api/loans'
import { fetchSets } from '../api/sets'
import type { LoanLine } from '../schemas/loan'
import { useInventoryQueryKey } from '../composables/useInventoryQueryKey'

const route = useRoute()
const { t } = useI18n()
const queryClient = useQueryClient()

const inventoryId = computed(() => Number(route.params.id))
const loanId = computed(() => Number(route.params.loanId))

const { data: loan, isLoading } = useQuery({
  queryKey: ['loan', loanId],
  queryFn: () => fetchLoan(loanId.value),
  enabled: () => Number.isFinite(loanId.value),
})

const setsQueryKey = useInventoryQueryKey('sets', inventoryId)
const piecesQueryKey = useInventoryQueryKey('pieces', inventoryId)
const materialTypesQueryKey = useInventoryQueryKey('materialTypes', inventoryId)

const { data: sets } = useQuery({
  queryKey: setsQueryKey,
  queryFn: () => fetchSets(inventoryId.value),
  enabled: () => Number.isFinite(inventoryId.value),
})

const { data: pieces } = useQuery({
  queryKey: piecesQueryKey,
  queryFn: () => fetchPieces(inventoryId.value),
  enabled: () => Number.isFinite(inventoryId.value),
})

const { data: materialTypes } = useQuery({
  queryKey: materialTypesQueryKey,
  queryFn: () => fetchMaterialTypes(inventoryId.value),
  enabled: () => Number.isFinite(inventoryId.value),
})

const addSetId = ref('')
const addOptionalSetId = ref('')
const addPieceId = ref('')
const addStockTypeId = ref('')
const addStockQty = ref('1')

const returnRecordedOn = ref(new Date().toISOString().slice(0, 10))
const returnOutcomes = reactive<Record<number, 'returned' | 'loss' | ''>>({})
const returnQuantities = reactive<Record<number, string>>({})

const isPlanned = computed(() => loan.value?.status === 'planned')
const isHandedOut = computed(() => loan.value?.status === 'handed_out')
const isClosed = computed(() => loan.value?.status === 'closed')

const kindLabel = computed(() => {
  const kind = loan.value?.kind
  if (kind === 'permanent') return t('loans.kindPermanent')
  return t('loans.kindShort')
})

const statusLabel = computed(() => {
  const status = loan.value?.status
  if (status === 'handed_out') return t('loans.statusHandedOut')
  if (status === 'closed') return t('loans.statusClosed')
  return t('loans.statusPlanned')
})

const stockTypes = computed(() =>
  (materialTypes.value ?? []).filter((mt) => mt.tracking === 'stock'),
)

const outstandingLines = computed(() =>
  (loan.value?.lines ?? []).filter((line) => !line.settled),
)

type LineGroup = { setId: number; setName: string; lines: LoanLine[] }

const lineGroups = computed(() => {
  const lines = loan.value?.lines ?? []
  const loose: LoanLine[] = []
  const bySet = new Map<number, LineGroup>()
  for (const line of lines) {
    const sid = line.originSetId
    if (sid == null) {
      loose.push(line)
      continue
    }
    let group = bySet.get(sid)
    if (!group) {
      group = { setId: sid, setName: line.originSetName ?? '', lines: [] }
      bySet.set(sid, group)
    }
    group.lines.push(line)
  }
  return { loose, groups: [...bySet.values()] }
})

const setsForOptionalAdd = computed(() => {
  const onLoan = new Set(
    (loan.value?.lines ?? [])
      .filter((l) => l.originSetId != null && l.originSetRole === 'assignment')
      .map((l) => l.originSetId as number),
  )
  return (sets.value ?? []).filter((s) => onLoan.has(s.id))
})

watch(
  outstandingLines,
  (lines) => {
    for (const line of lines) {
      if (returnOutcomes[line.id] === undefined) {
        returnOutcomes[line.id] = ''
      }
      if (line.kind === 'stock' && returnQuantities[line.id] === undefined) {
        returnQuantities[line.id] = ''
      }
    }
  },
  { immediate: true },
)

function lineLabel(line: LoanLine): string {
  if (line.kind === 'piece') return `${line.pieceName} · ${line.materialTypeName}`
  return `${line.materialTypeName} × ${line.quantity}`
}

function optionalTag(line: LoanLine): boolean {
  return line.originSetRole === 'optional'
}

function returnEntryLabel(line: LoanLine, outcome: string, quantity: number | null): string {
  const base = lineLabel(line)
  if (outcome === 'loss') {
    if (line.kind === 'stock' && quantity != null) {
      return t('loans.returnHistoryLossStock', { label: base, quantity })
    }
    return t('loans.returnHistoryLoss', { label: base })
  }
  if (line.kind === 'stock' && quantity != null) {
    return t('loans.returnHistoryReturnedStock', { label: base, quantity })
  }
  return t('loans.returnHistoryReturned', { label: base })
}

async function invalidate() {
  await queryClient.invalidateQueries({ queryKey: ['loan', loanId.value] })
  await queryClient.invalidateQueries({ queryKey: ['loans', inventoryId.value] })
}

const handOutMutation = useMutation({
  mutationFn: () => handOutLoan(loanId.value),
  onSuccess: invalidate,
})

const addSetMutation = useMutation({
  mutationFn: () => addLoanSetAssignmentLines(loanId.value, Number(addSetId.value)),
  onSuccess: async () => {
    addSetId.value = ''
    await invalidate()
  },
})

const addOptionalSetMutation = useMutation({
  mutationFn: () => addLoanSetOptionalLines(loanId.value, Number(addOptionalSetId.value)),
  onSuccess: async () => {
    addOptionalSetId.value = ''
    await invalidate()
  },
})

const addPieceMutation = useMutation({
  mutationFn: () => addLoanPieceLine(loanId.value, Number(addPieceId.value)),
  onSuccess: async () => {
    addPieceId.value = ''
    await invalidate()
  },
})

const addStockMutation = useMutation({
  mutationFn: () =>
    addLoanStockLine(loanId.value, Number(addStockTypeId.value), Number(addStockQty.value)),
  onSuccess: async () => {
    addStockTypeId.value = ''
    addStockQty.value = '1'
    await invalidate()
  },
})

const removeMutation = useMutation({
  mutationFn: (lineId: number) => removeLoanLine(loanId.value, lineId),
  onSuccess: invalidate,
})

function buildReturnEntries() {
  return outstandingLines.value
    .map((line) => {
      const outcome = returnOutcomes[line.id]
      if (outcome !== 'returned' && outcome !== 'loss') return null
      if (line.kind === 'stock') {
        const qty = Number(returnQuantities[line.id])
        if (!Number.isFinite(qty) || qty <= 0) return null
        if (qty > line.outstandingQuantity) return null
        return { loanLineId: line.id, outcome, quantity: qty }
      }
      return { loanLineId: line.id, outcome }
    })
    .filter((e): e is NonNullable<typeof e> => e !== null)
}

const returnMutation = useMutation({
  mutationFn: () => {
    const entries = buildReturnEntries()
    if (!entries.length) {
      throw new Error('no_return_entries')
    }
    return recordLoanReturn(loanId.value, {
      recordedOn: returnRecordedOn.value,
      entries,
    })
  },
  onSuccess: async () => {
    for (const key of Object.keys(returnOutcomes)) {
      delete returnOutcomes[Number(key)]
    }
    for (const key of Object.keys(returnQuantities)) {
      delete returnQuantities[Number(key)]
    }
    await invalidate()
  },
})
</script>

<template>
  <div class="app-page space-y-6">
    <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
    <template v-else-if="loan">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p class="text-sm text-base-content/70">{{ kindLabel }} · {{ statusLabel }}</p>
          <p class="text-lg font-semibold">{{ loan.groupName }}</p>
          <p class="text-sm">
            {{ t('loans.responsible') }}: {{ loan.responsibleUserName }}
            <template v-if="loan.eventName"> · {{ loan.eventName }}</template>
          </p>
        </div>
        <button
          v-if="isPlanned"
          type="button"
          class="btn btn-primary"
          :disabled="handOutMutation.isPending.value || !loan.lines.length"
          @click="handOutMutation.mutate()"
        >
          {{ t('loans.handOut') }}
        </button>
      </div>

      <section class="card bg-base-100 shadow-md">
        <div class="card-body gap-3 text-left">
          <h2 class="card-title text-base">{{ t('loans.linesHeading') }}</h2>
          <div class="space-y-4 text-sm">
            <div v-for="group in lineGroups.groups" :key="group.setId" class="space-y-2">
              <p class="font-semibold text-base-content/90">
                {{ t('sets.heading') }}: {{ group.setName }}
              </p>
              <ul class="space-y-2 pl-2">
                <li
                  v-for="line in group.lines"
                  :key="line.id"
                  class="rounded-lg bg-base-200/50 p-3"
                >
                  <div class="flex justify-between gap-2">
                    <span>
                      <template v-if="line.kind === 'piece'">
                        {{ line.pieceName }} · {{ line.materialTypeName }}
                      </template>
                      <template v-else>
                        {{ line.materialTypeName }} × {{ line.quantity }}
                      </template>
                      <span v-if="optionalTag(line)" class="ml-1 text-xs opacity-70">
                        ({{ t('sets.optionals') }})
                      </span>
                    </span>
                    <button
                      v-if="isPlanned"
                      type="button"
                      class="btn btn-ghost btn-xs"
                      @click="removeMutation.mutate(line.id)"
                    >
                      {{ t('sets.remove') }}
                    </button>
                  </div>
                  <p v-if="isHandedOut || isClosed" class="mt-2 text-xs opacity-80">
                    <template v-if="line.kind === 'stock'">
                      {{ t('loans.outstandingStock', { count: line.outstandingQuantity }) }}
                      <template v-if="line.returnedQuantity || line.lostQuantity">
                        ·
                        {{
                          t('loans.returnedSoFar', {
                            returned: line.returnedQuantity,
                            lost: line.lostQuantity,
                          })
                        }}
                      </template>
                    </template>
                    <template v-else-if="line.settled">
                      <template v-if="line.lostQuantity">{{ t('loans.lineSettledLoss') }}</template>
                      <template v-else>{{ t('loans.lineSettledReturned') }}</template>
                    </template>
                    <template v-else>{{ t('loans.outstandingPiece') }}</template>
                  </p>
                </li>
              </ul>
            </div>
            <ul v-if="lineGroups.loose.length" class="space-y-2">
              <li
                v-for="line in lineGroups.loose"
                :key="line.id"
                class="rounded-lg bg-base-200/50 p-3"
              >
                <div class="flex justify-between gap-2">
                  <span>
                    <template v-if="line.kind === 'piece'">
                      {{ line.pieceName }} · {{ line.materialTypeName }}
                    </template>
                    <template v-else>
                      {{ line.materialTypeName }} × {{ line.quantity }}
                    </template>
                  </span>
                  <button
                    v-if="isPlanned"
                    type="button"
                    class="btn btn-ghost btn-xs"
                    @click="removeMutation.mutate(line.id)"
                  >
                    {{ t('sets.remove') }}
                  </button>
                </div>
                <p v-if="isHandedOut || isClosed" class="mt-2 text-xs opacity-80">
                  <template v-if="line.kind === 'stock'">
                    {{ t('loans.outstandingStock', { count: line.outstandingQuantity }) }}
                    <template v-if="line.returnedQuantity || line.lostQuantity">
                      ·
                      {{
                        t('loans.returnedSoFar', {
                          returned: line.returnedQuantity,
                          lost: line.lostQuantity,
                        })
                      }}
                    </template>
                  </template>
                  <template v-else-if="line.settled">
                    <template v-if="line.lostQuantity">{{ t('loans.lineSettledLoss') }}</template>
                    <template v-else>{{ t('loans.lineSettledReturned') }}</template>
                  </template>
                  <template v-else>{{ t('loans.outstandingPiece') }}</template>
                </p>
              </li>
            </ul>
            <p v-if="!loan.lines.length" class="opacity-70">{{ t('loans.linesEmpty') }}</p>
          </div>
        </div>
      </section>

      <section v-if="isHandedOut && outstandingLines.length" class="card bg-base-100 shadow-md">
        <div class="card-body gap-4 text-left">
          <h2 class="card-title text-base">{{ t('loans.returnHeading') }}</h2>
          <form class="space-y-4" @submit.prevent="returnMutation.mutate()">
            <label class="form-control w-full max-w-xs">
              <span class="label-text">{{ t('loans.returnRecordedOn') }}</span>
              <input v-model="returnRecordedOn" type="date" class="input input-bordered" required />
            </label>
            <ul class="space-y-3 text-sm">
              <li
                v-for="line in outstandingLines"
                :key="line.id"
                class="rounded-lg bg-base-200/50 p-3 space-y-2"
              >
                <p class="font-medium">{{ lineLabel(line) }}</p>
                <p v-if="line.kind === 'stock'" class="text-xs opacity-80">
                  {{ t('loans.outstandingStock', { count: line.outstandingQuantity }) }}
                </p>
                <div class="flex flex-wrap items-center gap-2">
                  <select v-model="returnOutcomes[line.id]" class="select select-bordered select-sm">
                    <option disabled value="">{{ t('loans.pickReturnOutcome') }}</option>
                    <option value="returned">{{ t('loans.outcomeReturned') }}</option>
                    <option value="loss">{{ t('loans.outcomeLoss') }}</option>
                  </select>
                  <input
                    v-if="line.kind === 'stock'"
                    v-model="returnQuantities[line.id]"
                    type="number"
                    min="1"
                    :max="line.outstandingQuantity"
                    class="input input-bordered input-sm w-24"
                    :placeholder="t('loans.returnQuantity')"
                  />
                </div>
              </li>
            </ul>
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="returnMutation.isPending.value"
            >
              {{ t('loans.submitReturn') }}
            </button>
          </form>
        </div>
      </section>

      <section v-if="loan.returns.length" class="card bg-base-100 shadow-md">
        <div class="card-body gap-3 text-left">
          <h2 class="card-title text-base">{{ t('loans.returnHistoryHeading') }}</h2>
          <ul class="space-y-3 text-sm">
            <li
              v-for="ret in loan.returns"
              :key="ret.id"
              class="rounded-lg bg-base-200/50 p-3"
            >
              <p class="font-medium">{{ ret.recordedOn }}</p>
              <ul class="mt-1 space-y-1 pl-2 text-xs opacity-90">
                <li v-for="(entry, idx) in ret.lines" :key="idx">
                  {{
                    returnEntryLabel(
                      loan.lines.find((l) => l.id === entry.loanLineId)!,
                      entry.outcome,
                      entry.quantity,
                    )
                  }}
                </li>
              </ul>
            </li>
          </ul>
        </div>
      </section>

      <section v-if="isPlanned" class="card bg-base-100 shadow-md">
        <div class="card-body gap-4 text-left">
          <h2 class="card-title text-base">{{ t('loans.addLine') }}</h2>
          <form class="flex flex-wrap gap-2" @submit.prevent="addSetMutation.mutate()">
            <select v-model="addSetId" class="select select-bordered min-w-0 flex-1" required>
              <option disabled value="">{{ t('loans.pickSet') }}</option>
              <option v-for="s in sets" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
            <button type="submit" class="btn btn-outline" :disabled="addSetMutation.isPending.value">
              {{ t('loans.addSet') }}
            </button>
          </form>
          <form
            v-if="setsForOptionalAdd.length"
            class="flex flex-wrap gap-2"
            @submit.prevent="addOptionalSetMutation.mutate()"
          >
            <select
              v-model="addOptionalSetId"
              class="select select-bordered min-w-0 flex-1"
              required
            >
              <option disabled value="">{{ t('loans.pickSetForOptionals') }}</option>
              <option v-for="s in setsForOptionalAdd" :key="s.id" :value="s.id">
                {{ s.name }}
              </option>
            </select>
            <button
              type="submit"
              class="btn btn-outline"
              :disabled="addOptionalSetMutation.isPending.value"
            >
              {{ t('loans.addSetOptionals') }}
            </button>
          </form>
          <form class="flex flex-wrap gap-2" @submit.prevent="addPieceMutation.mutate()">
            <select v-model="addPieceId" class="select select-bordered min-w-0 flex-1" required>
              <option disabled value="">{{ t('loans.pickPiece') }}</option>
              <option v-for="p in pieces" :key="p.id" :value="p.id">
                {{ p.name }} · {{ p.materialTypeName }}
              </option>
            </select>
            <button type="submit" class="btn btn-outline" :disabled="addPieceMutation.isPending.value">
              {{ t('loans.addPiece') }}
            </button>
          </form>
          <form class="flex flex-wrap gap-2" @submit.prevent="addStockMutation.mutate()">
            <select v-model="addStockTypeId" class="select select-bordered min-w-0 flex-1" required>
              <option disabled value="">{{ t('loans.pickStockType') }}</option>
              <option v-for="mt in stockTypes" :key="mt.id" :value="mt.id">{{ mt.name }}</option>
            </select>
            <input
              v-model="addStockQty"
              type="number"
              min="1"
              class="input input-bordered w-24"
              required
            />
            <button type="submit" class="btn btn-outline" :disabled="addStockMutation.isPending.value">
              {{ t('loans.addStock') }}
            </button>
          </form>
        </div>
      </section>
    </template>
  </div>
</template>
