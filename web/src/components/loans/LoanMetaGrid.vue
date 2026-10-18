<script setup lang="ts">
import { useMutation, useQuery } from '@tanstack/vue-query'
import { computed, ref, watch, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchBorrowers, fetchGroups, patchLoan } from '../../api/loans'
import { fetchMe } from '../../api/me'
import type { LoanDetail } from '../../schemas/loan'
import { useApiErrorMessage } from '../../composables/useApiErrorMessage'
import ContextHelp from '../ContextHelp.vue'
import NamedOptionCombobox from '../NamedOptionCombobox.vue'
import LoanDateField from './LoanDateField.vue'
import LoanDetailDisclosure from './LoanDetailDisclosure.vue'
import { loanMetaSectionOpen } from '../../utils/loanDetailSectionOpen'

type LoanDateFieldExpose = InstanceType<typeof LoanDateField> & {
  focusAndShowPicker: (options?: { anchorDate?: string }) => void
}

const props = defineProps<{
  loan: LoanDetail
  canManage: boolean
  canEditBorrower: boolean
  isLoanBorrower: boolean
  permissionUsers: { id: number; name?: string | null; email?: string | null }[]
}>()

const emit = defineEmits<{
  saved: []
}>()

const { t } = useI18n()
const { messageFor } = useApiErrorMessage()
const error = ref<string | null>(null)

const groupName = ref('')
const eventName = ref('')
const loanKind = ref<'short' | 'permanent'>('short')
const contactUserId = ref('')
const borrowerUserId = ref('')
const wishPickupOn = ref('')
const wishReturnOn = ref('')
const termPickupOn = ref('')
const termReturnOn = ref('')

const wishReturnField = ref<LoanDateFieldExpose | null>(null)
const termReturnField = ref<LoanDateFieldExpose | null>(null)

function chainToReturnAfterPickup(
  pickupValue: string,
  returnField: Ref<LoanDateFieldExpose | null>,
) {
  if (!pickupValue.trim()) return
  returnField.value?.focusAndShowPicker({ anchorDate: pickupValue })
}

function afterWishPickupCommitted(pickupValue: string) {
  chainToReturnAfterPickup(pickupValue, wishReturnField)
}

function afterTermPickupCommitted(pickupValue: string) {
  chainToReturnAfterPickup(pickupValue, termReturnField)
}

watch(
  () => props.loan,
  (loan) => {
    groupName.value = loan.groupName === '—' ? '' : loan.groupName
    eventName.value = loan.eventName ?? ''
    loanKind.value = loan.kind
    contactUserId.value = loan.contactUserId != null ? String(loan.contactUserId) : ''
    borrowerUserId.value = String(loan.borrowerUserId)
    wishPickupOn.value = loan.wishPickupOn ?? loan.pickupOn ?? ''
    wishReturnOn.value = loan.wishReturnOn ?? loan.returnOn ?? ''
    termPickupOn.value = loan.pickupOn ?? ''
    termReturnOn.value = loan.returnOn ?? ''
  },
  { immediate: true },
)

const { data: me } = useQuery({ queryKey: ['me'], queryFn: fetchMe })
const { data: borrowers } = useQuery({
  queryKey: ['borrowers'],
  queryFn: fetchBorrowers,
  enabled: () => props.canManage && props.loan.phase === 'draft',
})

const borrowerOptions = computed(() => {
  const rows = [...(borrowers.value ?? [])]
  if (me.value && !rows.some((row) => row.id === me.value?.id)) {
    rows.unshift(me.value)
  }
  return rows
})

const isDraft = computed(() => props.loan.phase === 'draft')
const isLegacyManagerDraftForOther = computed(
  () =>
    props.canManage &&
    isDraft.value &&
    me.value != null &&
    props.loan.contactUserId === me.value.id &&
    props.loan.borrowerUserId !== me.value.id,
)
const canChangeBorrower = computed(() => props.canManage && isDraft.value)
const borrowerHandoffPending = computed(() => {
  if (!canChangeBorrower.value || me.value == null) return false
  const selected = Number(borrowerUserId.value)
  return selected !== props.loan.borrowerUserId && selected !== me.value.id
})
const isClosed = computed(() => props.loan.phase === 'closed')
const canEditManager = computed(() => props.canManage && !isClosed.value && !isDraft.value)
const canEditLoanBlock = computed(
  () => !isClosed.value && props.canEditBorrower && isDraft.value,
)
const canEditLoanMeta = computed(() => canEditLoanBlock.value || canEditManager.value)
const isPermanent = computed(() => loanKind.value === 'permanent')
const canEditWishDates = computed(() => {
  if (isPermanent.value || isClosed.value) return false
  if (isDraft.value) return props.isLoanBorrower || props.canManage
  return canEditManager.value
})
const showWishDatesReadonly = computed(
  () =>
    !isPermanent.value &&
    !canEditWishDates.value &&
    Boolean(props.loan.wishPickupOn || props.loan.wishReturnOn),
)

const { data: groups } = useQuery({
  queryKey: ['groups'],
  queryFn: fetchGroups,
  enabled: () => canEditLoanMeta.value,
})

const groupOptions = computed(() => groups.value ?? [])

const displayGroup = computed(() => {
  const group = props.loan.groupName.trim()
  if (!group || group === '—') return null
  return group
})

const showManagerBlock = computed(
  () => props.canManage && !isClosed.value && !isDraft.value,
)

const metaDetailsOpen = computed(() => loanMetaSectionOpen(props.loan.phase))

const metaSummaryParts = computed(() => {
  const parts: string[] = []
  const group = displayGroup.value
  if (group) parts.push(group)
  if (props.loan.eventName?.trim()) parts.push(props.loan.eventName.trim())
  const pickup = props.loan.wishPickupOn ?? props.loan.pickupOn
  const returnDate = props.loan.wishReturnOn ?? props.loan.returnOn
  if (pickup) parts.push(t('loans.pickupOnWish') + ': ' + pickup)
  if (returnDate && props.loan.kind !== 'permanent') {
    parts.push(t('loans.returnOnWish') + ': ' + returnDate)
  }
  return parts.join(' · ')
})

function buildLoanPayload(): Record<string, unknown> {
  if (!canEditLoanMeta.value) return {}
  const payload: Record<string, unknown> = {
    groupName: groupName.value.trim() || '—',
    kind: loanKind.value,
  }
  if (isPermanent.value) {
    payload.clearEvent = true
    payload.returnOn = null
  } else if (eventName.value.trim()) {
    payload.eventName = eventName.value.trim()
  } else {
    payload.clearEvent = true
  }
  if (canEditWishDates.value) {
    payload.wishPickupOn = wishPickupOn.value || null
    if (!isPermanent.value) {
      payload.wishReturnOn = wishReturnOn.value || null
    }
  }
  if (isDraft.value && isLegacyManagerDraftForOther.value) {
    payload.pickupOn = wishPickupOn.value || null
    if (!isPermanent.value) {
      payload.returnOn = wishReturnOn.value || null
    }
  }
  return payload
}

function selectedBorrowerId(): number {
  return Number(borrowerUserId.value)
}

function willHandDraftToBorrower(newBorrowerId: number): boolean {
  if (!isDraft.value || me.value == null) return false
  return props.loan.borrowerUserId === me.value.id && newBorrowerId !== me.value.id
}

function buildCarePayload(): Record<string, unknown> {
  if (!canEditManager.value) return {}
  const payload: Record<string, unknown> = {}
  const raw = contactUserId.value.trim()
  if (raw) payload.contactUserId = Number(raw)
  const termPickup = termPickupOn.value.trim()
  const termReturn = termReturnOn.value.trim()
  if (!isPermanent.value && (termPickup || termReturn)) {
    payload.pickupOn = termPickup || null
    payload.returnOn = termReturn || null
  } else if (isPermanent.value && termPickup) {
    payload.pickupOn = termPickup
  }
  if (Object.keys(payload).length === 0) return {}
  return payload
}

function validateDatePair(pickup: string, returnDate: string): boolean {
  if (pickup && !returnDate) {
    error.value = t('loans.errors.return_required')
    return false
  }
  if (returnDate && !pickup) {
    error.value = t('loans.errors.pickup_required')
    return false
  }
  return true
}

function validateDatesBeforeSave() {
  if (isPermanent.value) return true
  if (canEditWishDates.value && (isDraft.value || canEditManager.value)) {
    if (!validateDatePair(wishPickupOn.value.trim(), wishReturnOn.value.trim())) {
      return false
    }
  }
  if (canEditManager.value) {
    if (!validateDatePair(termPickupOn.value.trim(), termReturnOn.value.trim())) {
      return false
    }
  }
  return true
}

const saveMutation = useMutation({
  mutationFn: async () => {
    if (!validateDatesBeforeSave()) {
      return Promise.reject(new Error('dates_invalid'))
    }
    const newBorrowerId = selectedBorrowerId()
    if (
      willHandDraftToBorrower(newBorrowerId) &&
      !window.confirm(t('loans.confirmHandoffBorrower'))
    ) {
      return Promise.reject(new Error('handoff_cancelled'))
    }
    const loanPayload = buildLoanPayload()
    const carePayload = buildCarePayload()
    let latest = props.loan
    if (Object.keys(loanPayload).length > 0) {
      latest = await patchLoan(props.loan.id, loanPayload)
    }
    if (Object.keys(carePayload).length > 0) {
      latest = await patchLoan(props.loan.id, carePayload)
    }
    if (canChangeBorrower.value && newBorrowerId !== props.loan.borrowerUserId) {
      latest = await patchLoan(props.loan.id, { borrowerUserId: newBorrowerId })
    }
    return latest
  },
  onSuccess: () => {
    error.value = null
    emit('saved')
  },
  onError: (err) => {
    if (err instanceof Error && err.message === 'handoff_cancelled') return
    if (err instanceof Error && err.message === 'dates_invalid') return
    error.value = messageFor(err)
  },
})

function onContactChange() {
  if (!canEditManager.value || !contactUserId.value.trim()) return
  // Persist contact together with any unsaved loan meta — a contact-only PATCH
  // would refetch and reset local fields (group, dates, title) via the loan watch.
  saveMutation.mutate()
}
</script>

<template>
  <LoanDetailDisclosure
    class="text-sm"
    :open="metaDetailsOpen"
    :title="t('loans.metaSectionDetails')"
    :subtitle="metaSummaryParts || null"
    title-variant="meta"
  >
    <div class="space-y-4">
    <div>
      <p class="mb-2 text-xs font-medium uppercase tracking-wide opacity-60">
        {{ t('loans.metaSectionLoan') }}
      </p>
      <dl
        v-if="canEditLoanMeta"
        class="grid grid-cols-2 gap-x-3 gap-y-2 sm:grid-cols-4"
      >
        <div v-if="!isPermanent" class="col-span-2 flex min-w-0 flex-col gap-1">
          <dt class="text-xs opacity-80">{{ t('loans.title') }}</dt>
          <dd class="m-0">
            <input
              v-model="eventName"
              type="text"
              class="input input-bordered input-sm w-full"
              :placeholder="t('loans.titlePlaceholder')"
            />
          </dd>
        </div>
        <div class="col-span-2 flex min-w-0 flex-col gap-1">
          <dt class="text-xs opacity-80">{{ t('loans.group') }}</dt>
          <dd class="m-0">
            <NamedOptionCombobox
              v-model="groupName"
              :options="groupOptions"
              :placeholder="t('loans.groupPlaceholder')"
              clear-label-key="loans.groupClear"
              empty-label-key="loans.groupEmpty"
              menu-label-key="loans.groupMenu"
              new-label-key="loans.groupNew"
              input-size="sm"
              required
            />
          </dd>
        </div>
        <div class="flex min-w-0 flex-col gap-1">
          <dt class="flex items-center gap-1 text-xs opacity-80">
            <span>{{ t('loans.kind') }}</span>
            <ContextHelp anchor="dauerleihgabe" :label="t('help.glossary.dauerleihgabe.title')" />
          </dt>
          <dd class="m-0">
            <select v-model="loanKind" class="select select-bordered select-sm w-full">
              <option value="short">{{ t('loans.kindShort') }}</option>
              <option value="permanent">{{ t('loans.kindPermanent') }}</option>
            </select>
          </dd>
        </div>
        <div class="flex min-w-0 flex-col gap-1">
          <dt class="text-xs opacity-80">{{ t('loans.borrower') }}</dt>
          <dd class="m-0 flex min-w-0 flex-col gap-1">
            <select
              v-if="canChangeBorrower"
              v-model="borrowerUserId"
              class="select select-bordered select-sm w-full"
              :disabled="saveMutation.isPending.value"
            >
              <option v-for="person in borrowerOptions" :key="person.id" :value="String(person.id)">
                {{ person.name || person.email }}
              </option>
            </select>
            <input
              v-else
              type="text"
              class="input input-bordered input-sm w-full min-w-0 truncate disabled:cursor-default disabled:border-base-300/60 disabled:bg-base-200/30 disabled:opacity-90"
              :value="loan.borrowerUserName"
              disabled
              readonly
            />
          </dd>
        </div>
        <template v-if="canEditWishDates">
          <div class="flex min-w-0 flex-col gap-1">
            <dt class="text-xs opacity-80">{{ t('loans.pickupOnWish') }}</dt>
            <dd class="m-0">
              <LoanDateField
                v-model="wishPickupOn"
                @committed="afterWishPickupCommitted"
              />
            </dd>
          </div>
          <div v-if="!isPermanent" class="flex min-w-0 flex-col gap-1">
            <dt class="text-xs opacity-80">{{ t('loans.returnOnWish') }}</dt>
            <dd class="m-0">
              <LoanDateField
                ref="wishReturnField"
                v-model="wishReturnOn"
                :min="wishPickupOn || undefined"
              />
            </dd>
          </div>
        </template>
      </dl>
      <dl v-else class="grid grid-cols-2 gap-x-3 gap-y-2 sm:grid-cols-4">
        <div v-if="displayGroup" class="col-span-2 flex min-w-0 flex-col gap-0.5">
          <dt class="text-xs opacity-80">{{ t('loans.group') }}</dt>
          <dd>{{ displayGroup }}</dd>
        </div>
        <div class="flex min-w-0 flex-col gap-1">
          <dt class="text-xs opacity-80">{{ t('loans.borrower') }}</dt>
          <dd class="m-0">
            <input
              type="text"
              class="input input-bordered input-sm w-full min-w-0 truncate disabled:cursor-default disabled:border-base-300/60 disabled:bg-base-200/30 disabled:opacity-90"
              :value="loan.borrowerUserName"
              disabled
              readonly
            />
          </dd>
        </div>
        <template v-if="showWishDatesReadonly">
          <div class="flex min-w-0 flex-col gap-1">
            <dt class="text-xs opacity-80">{{ t('loans.pickupOnWish') }}</dt>
            <dd class="m-0">
              <LoanDateField :model-value="loan.wishPickupOn ?? ''" disabled />
            </dd>
          </div>
          <div class="flex min-w-0 flex-col gap-1">
            <dt class="text-xs opacity-80">{{ t('loans.returnOnWish') }}</dt>
            <dd class="m-0">
              <LoanDateField :model-value="loan.wishReturnOn ?? ''" disabled />
            </dd>
          </div>
        </template>
      </dl>
    </div>

    <div v-if="showManagerBlock" class="border-t border-base-300/40 pt-4">
      <p class="mb-2 text-xs font-medium uppercase tracking-wide opacity-60">
        {{ t('loans.metaSectionCare') }}
      </p>
      <dl class="grid grid-cols-1 gap-x-3 gap-y-2 sm:grid-cols-3">
        <div class="flex min-w-0 flex-col gap-1">
          <dt class="text-xs opacity-80">{{ t('loans.contact') }}</dt>
          <dd class="m-0">
            <select
              v-model="contactUserId"
              class="select select-bordered select-sm w-full"
              :disabled="saveMutation.isPending.value"
              @change="onContactChange"
            >
              <option disabled value="">{{ t('loans.pickContact') }}</option>
              <option v-for="u in permissionUsers" :key="u.id" :value="String(u.id)">
                {{ u.name ?? u.email }}
              </option>
            </select>
          </dd>
        </div>
        <template v-if="!isPermanent">
          <div class="flex min-w-0 flex-col gap-1">
            <dt class="text-xs opacity-80">{{ t('loans.pickupOnDate') }}</dt>
            <dd class="m-0">
              <LoanDateField
                v-model="termPickupOn"
                @committed="afterTermPickupCommitted"
              />
            </dd>
          </div>
          <div class="flex min-w-0 flex-col gap-1">
            <dt class="text-xs opacity-80">{{ t('loans.returnOnDate') }}</dt>
            <dd class="m-0">
              <LoanDateField
                ref="termReturnField"
                v-model="termReturnOn"
                :min="termPickupOn || undefined"
              />
            </dd>
          </div>
        </template>
      </dl>
    </div>
    <div v-else-if="loan.contactUserName" class="border-t border-base-300/40 pt-4">
      <p class="mb-2 text-xs font-medium uppercase tracking-wide opacity-60">
        {{ t('loans.metaSectionCare') }}
      </p>
      <dl class="grid grid-cols-1 gap-x-3 gap-y-2 sm:grid-cols-3">
        <div class="flex min-w-0 flex-col gap-0.5">
          <dt class="text-xs opacity-80">{{ t('loans.contact') }}</dt>
          <dd>{{ loan.contactUserName }}</dd>
        </div>
        <template v-if="!isPermanent">
          <div class="flex min-w-0 flex-col gap-1">
            <dt class="text-xs opacity-80">{{ t('loans.pickupOnDate') }}</dt>
            <dd class="m-0">
              <LoanDateField :model-value="loan.pickupOn ?? ''" disabled />
            </dd>
          </div>
          <div class="flex min-w-0 flex-col gap-1">
            <dt class="text-xs opacity-80">{{ t('loans.returnOnDate') }}</dt>
            <dd class="m-0">
              <LoanDateField :model-value="loan.returnOn ?? ''" disabled />
            </dd>
          </div>
        </template>
      </dl>
    </div>

    <template v-if="canEditLoanBlock || canEditManager">
      <p v-if="error" class="text-sm text-error">{{ error }}</p>
      <div
        class="flex w-full flex-wrap items-center gap-x-3 gap-y-2"
        :class="borrowerHandoffPending ? 'justify-between' : 'justify-end'"
      >
        <p
          v-if="borrowerHandoffPending"
          class="min-w-0 flex-1 text-xs leading-snug opacity-80"
        >
          {{ t('loans.borrowerHandoffOnSave') }}
        </p>
        <button
          type="button"
          class="btn btn-primary btn-sm shrink-0"
          :disabled="saveMutation.isPending.value"
          @click="saveMutation.mutate()"
        >
          {{ t('material.save') }}
        </button>
      </div>
    </template>
    </div>
  </LoanDetailDisclosure>
</template>
