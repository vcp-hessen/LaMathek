<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { createLoan, fetchEvents, fetchGroups, fetchLoans, fetchVerantwortliche } from '../api/loans'
import { useInventoryQueryKey } from '../composables/useInventoryQueryKey'
import PhotoThumbnail from '../components/PhotoThumbnail.vue'

const props = defineProps<{ inventoryId: number }>()

const { t } = useI18n()
const router = useRouter()
const queryClient = useQueryClient()

const groupName = ref('')
const eventName = ref('')
const responsibleUserId = ref<string>('')
const startsOn = ref('')
const endsOn = ref('')
const loanKind = ref<'short' | 'permanent'>('short')

const isPermanentKind = computed(() => loanKind.value === 'permanent')

const loansQueryKey = useInventoryQueryKey('loans', () => props.inventoryId)

const { data: loans, isLoading } = useQuery({
  queryKey: loansQueryKey,
  queryFn: () => fetchLoans(props.inventoryId),
})

const { data: groups } = useQuery({ queryKey: ['groups'], queryFn: fetchGroups })
const { data: events } = useQuery({ queryKey: ['events'], queryFn: fetchEvents })
const { data: verantwortliche } = useQuery({
  queryKey: ['verantwortliche'],
  queryFn: fetchVerantwortliche,
})

const createMutation = useMutation({
  mutationFn: () =>
    createLoan(props.inventoryId, {
      groupName: groupName.value,
      responsibleUserId: Number(responsibleUserId.value),
      kind: loanKind.value,
      eventName: isPermanentKind.value ? undefined : eventName.value.trim() || undefined,
      startsOn: isPermanentKind.value ? undefined : startsOn.value || undefined,
      endsOn: isPermanentKind.value ? undefined : endsOn.value || undefined,
    }),
  onSuccess: async (loan) => {
    groupName.value = ''
    eventName.value = ''
    responsibleUserId.value = ''
    startsOn.value = ''
    endsOn.value = ''
    loanKind.value = 'short'
    await queryClient.invalidateQueries({ queryKey: ['loans', props.inventoryId] })
    await router.push(`/inventories/${props.inventoryId}/loans/${loan.id}`)
  },
})

const sortedLoans = computed(() =>
  [...(loans.value ?? [])].sort((a, b) => b.id - a.id),
)

function statusLabel(status: string) {
  if (status === 'handed_out') return t('loans.statusHandedOut')
  if (status === 'closed') return t('loans.statusClosed')
  return t('loans.statusPlanned')
}

function kindLabel(kind: string) {
  return kind === 'permanent' ? t('loans.kindPermanent') : t('loans.kindShort')
}
</script>

<template>
  <div class="app-page space-y-6">
    <h1 class="text-2xl font-bold">{{ t('loans.heading') }}</h1>

    <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
    <ul v-else class="menu rounded-box bg-base-100 shadow">
      <li v-for="loan in sortedLoans" :key="loan.id">
        <RouterLink :to="`/inventories/${inventoryId}/loans/${loan.id}`" class="flex items-center gap-3">
          <PhotoThumbnail :photo-id="loan.coverPhotoId" />
          <span class="flex flex-1 flex-col gap-0.5">
            <span>{{ loan.groupName }} · {{ loan.responsibleUserName }}</span>
            <span class="text-xs opacity-70">
              {{ kindLabel(loan.kind) }} · {{ statusLabel(loan.status) }}
              <template v-if="loan.eventName"> · {{ loan.eventName }}</template>
            </span>
          </span>
        </RouterLink>
      </li>
      <li v-if="!sortedLoans.length" class="px-4 py-3 text-sm opacity-70">
        {{ t('loans.empty') }}
      </li>
    </ul>

    <form class="card bg-base-100 shadow-md" @submit.prevent="createMutation.mutate()">
      <div class="card-body gap-3 text-left">
        <h2 class="card-title text-base">{{ t('loans.create') }}</h2>
        <label class="form-control">
          <span class="label-text">{{ t('loans.group') }}</span>
          <input
            v-model="groupName"
            type="text"
            class="input input-bordered"
            :placeholder="t('loans.groupPlaceholder')"
            list="loan-groups"
            required
          />
          <datalist id="loan-groups">
            <option v-for="g in groups" :key="g.id" :value="g.name" />
          </datalist>
        </label>
        <label class="form-control">
          <span class="label-text">{{ t('loans.kind') }}</span>
          <select v-model="loanKind" class="select select-bordered">
            <option value="short">{{ t('loans.kindShort') }}</option>
            <option value="permanent">{{ t('loans.kindPermanent') }}</option>
          </select>
        </label>
        <label class="form-control">
          <span class="label-text">{{ t('loans.responsible') }}</span>
          <select v-model="responsibleUserId" class="select select-bordered" required>
            <option disabled value="">{{ t('loans.pickResponsible') }}</option>
            <option v-for="u in verantwortliche" :key="u.id" :value="u.id">
              {{ u.name ?? u.email ?? u.sub }}
            </option>
          </select>
        </label>
        <template v-if="!isPermanentKind">
          <label class="form-control">
            <span class="label-text">{{ t('loans.event') }}</span>
            <input
              v-model="eventName"
              type="text"
              class="input input-bordered"
              :placeholder="t('loans.eventOptional')"
              list="loan-events"
            />
            <datalist id="loan-events">
              <option v-for="e in events" :key="e.id" :value="e.name" />
            </datalist>
          </label>
          <div class="grid gap-3 sm:grid-cols-2">
            <label class="form-control">
              <span class="label-text">{{ t('loans.startsOn') }}</span>
              <input v-model="startsOn" type="date" class="input input-bordered" />
            </label>
            <label class="form-control">
              <span class="label-text">{{ t('loans.endsOn') }}</span>
              <input v-model="endsOn" type="date" class="input input-bordered" />
            </label>
          </div>
        </template>
        <button type="submit" class="btn btn-primary" :disabled="createMutation.isPending.value">
          {{ t('loans.create') }}
        </button>
      </div>
    </form>
  </div>
</template>
