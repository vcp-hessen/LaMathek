<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useActiveBox } from '../../composables/useActiveBox'
import { useCreateMinimalLoan } from '../../composables/useCreateMinimalLoan'
import { useInventoryCanManage } from '../../composables/useInventoryCanManage'
import { useApiErrorMessage } from '../../composables/useApiErrorMessage'
import { isInventoryWorkspaceRoute } from '../../utils/inventoryWorkspaceRoutes'
import type { Loan } from '../../schemas/loan'
import { loanDisplayName } from '../../utils/loanDisplayName'
import { loanPhaseLabelKey } from '../../utils/loanPhaseLabel'
import UiIcon from '../UiIcon.vue'
import WlzIcon from '../WlzIcon.vue'

const props = defineProps<{
  inventoryId: number
  showWhenLoggedIn: boolean
}>()

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { messageFor } = useApiErrorMessage()

const detailsRef = ref<HTMLDetailsElement | null>(null)
const createError = ref<string | null>(null)

const visible = computed(
  () =>
    props.showWhenLoggedIn &&
    Number.isFinite(props.inventoryId) &&
    isInventoryWorkspaceRoute(route.name),
)

const { canManage, inventories } = useInventoryCanManage(() => props.inventoryId)
const inventory = computed(() => inventories.value?.find((row) => row.id === props.inventoryId))
const canUseLoans = computed(() => inventory.value != null && inventory.value.visibility !== 'archived')

const {
  eligibleLoans,
  activeLoanId,
  activeLoanSummary,
  lineCount,
  setActiveLoan,
} = useActiveBox(() => props.inventoryId)

const createMutation = useCreateMinimalLoan(props.inventoryId)

const boxGlyph = computed(() => (lineCount.value > 0 ? 'full' : 'empty'))

function closeDropdown() {
  const root = detailsRef.value
  if (root?.open) root.open = false
}

function closeOnClickOutside(event: MouseEvent) {
  const root = detailsRef.value
  if (!root?.open) return
  const target = event.target
  if (target instanceof Node && root.contains(target)) return
  root.open = false
}

function closeOnEscape(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  const root = detailsRef.value
  if (root?.open) root.open = false
}

onMounted(() => {
  document.addEventListener('click', closeOnClickOutside, true)
  document.addEventListener('keydown', closeOnEscape)
})

onUnmounted(() => {
  document.removeEventListener('click', closeOnClickOutside, true)
  document.removeEventListener('keydown', closeOnEscape)
})

function phaseLabel(phase: Loan['phase']) {
  return t(loanPhaseLabelKey(phase))
}

function selectLoan(loanId: number) {
  setActiveLoan(loanId)
  closeDropdown()
}

function clearSelection() {
  setActiveLoan(null)
  closeDropdown()
}

async function onNewLoan() {
  createError.value = null
  try {
    const loan = await createMutation.mutateAsync()
    closeDropdown()
    await router.push(`/inventories/${props.inventoryId}/loans/${loan.id}`)
  } catch (error) {
    createError.value = messageFor(error)
  }
}

const buttonLabel = computed(() => {
  if (activeLoanSummary.value) {
    return loanDisplayName(activeLoanSummary.value) || activeLoanSummary.value.groupName
  }
  return t('loans.pickBox')
})

function loanDetailPath(loanId: number) {
  return `/inventories/${props.inventoryId}/loans/${loanId}`
}

function loanRowMeta(loan: Loan): string {
  const parts = [phaseLabel(loan.phase)]
  if (canManage.value) parts.push(loan.borrowerUserName)
  return parts.join(' · ')
}
</script>

<template>
  <details
    v-if="visible && canUseLoans"
    ref="detailsRef"
    class="dropdown dropdown-end group min-w-0 flex-none max-w-[min(20rem,calc(100vw-4.5rem))] sm:w-80 sm:max-w-[calc(100vw-1rem)]"
    :class="activeLoanId != null ? 'max-sm:w-auto max-sm:max-w-none' : ''"
    @click.stop
  >
    <summary
      class="btn btn-ghost btn-sm w-full gap-2 border-0 px-2.5 shadow-none outline-none focus:outline-none focus-visible:outline-none normal-case [&::-webkit-details-marker]:hidden sm:justify-between"
      :class="[
        activeLoanId != null ? 'bg-base-200/70 max-sm:px-2' : '',
        activeLoanId == null ? 'justify-between' : 'max-sm:justify-start sm:justify-between',
      ]"
      :aria-label="
        activeLoanId != null
          ? `${t('loans.pickBox')}: ${buttonLabel}`
          : t('loans.pickBox')
      "
    >
      <WlzIcon :glyph="boxGlyph" size-class="text-base shrink-0" />
      <span
        class="min-w-0 flex-1 truncate text-sm font-medium leading-snug"
        :class="activeLoanId != null ? 'hidden sm:block' : ''"
      >
        {{ buttonLabel }}
      </span>
          <span
            v-if="activeLoanId != null"
            class="badge badge-sm badge-ghost shrink-0 tabular-nums"
          >
            {{ lineCount }}
          </span>
          <UiIcon
            name="chevronDown"
            class="size-4 shrink-0 opacity-60 transition-transform group-open:rotate-180"
          />
    </summary>
    <div
      class="dropdown-content z-30 mt-1 w-[calc(100vw-0.5rem)] max-w-none rounded-box border border-base-200 bg-base-100 p-2 shadow-sm sm:w-80 sm:max-w-[calc(100vw-1rem)] sm:shadow-lg"
      @click.stop
    >
      <div class="mb-2 flex items-center gap-2 px-0.5">
        <p class="min-w-0 flex-1 text-xs font-medium opacity-70">{{ t('loans.pickBox') }}</p>
        <button
          type="button"
          class="btn btn-ghost btn-square btn-xs shrink-0"
          :disabled="createMutation.isPending.value"
          :aria-label="t('loans.newDraft')"
          :title="t('loans.newDraft')"
          @click="onNewLoan"
        >
          <UiIcon name="plus" size-class="size-4" />
        </button>
      </div>
      <p v-if="createError" class="mb-2 text-xs text-error">{{ createError }}</p>
      <ul class="flex max-h-72 w-full flex-col gap-0.5 overflow-y-auto p-0">
        <li v-for="loan in eligibleLoans" :key="loan.id" class="w-full list-none">
          <div
            class="flex w-full items-center gap-1 rounded-lg pr-2 hover:bg-base-200/80"
            :class="{ 'bg-base-200/90': loan.id === activeLoanId }"
          >
            <button
              type="button"
              class="btn btn-ghost btn-xs btn-square shrink-0"
              :aria-label="t('loans.useAsBox')"
              :title="t('loans.useAsBox')"
              @click="selectLoan(loan.id)"
            >
              <span
                class="block size-2.5 rounded-full border-2"
                :class="
                  loan.id === activeLoanId
                    ? 'border-primary bg-primary'
                    : 'border-base-content/25 bg-transparent'
                "
              />
            </button>
            <RouterLink
              :to="loanDetailPath(loan.id)"
              class="min-w-0 flex-1 py-2 text-sm leading-snug hover:underline"
              :title="t('loans.openLoan')"
              @click="closeDropdown"
            >
              <span class="block truncate">
                <span class="font-medium">{{ loanDisplayName(loan) || loan.groupName }}</span>
                <span class="font-normal opacity-60"> · {{ loanRowMeta(loan) }}</span>
              </span>
            </RouterLink>
          </div>
        </li>
        <li v-if="!eligibleLoans.length" class="w-full list-none">
          <span class="block px-3 py-2 text-xs opacity-70">{{ t('loans.noEligibleBox') }}</span>
        </li>
        <li class="w-full list-none">
          <button
            type="button"
            class="flex w-full items-center gap-1 rounded-lg border border-transparent py-2 pl-1 pr-2 text-left hover:bg-base-200/80"
            :class="
              activeLoanId == null
                ? 'border-dashed border-base-300/80 bg-base-200/50'
                : 'opacity-80'
            "
            @click="clearSelection"
          >
            <span class="btn btn-ghost btn-xs btn-square pointer-events-none shrink-0">
              <span
                class="block size-2.5 rounded-full border-2 border-dashed border-base-content/35"
                :class="activeLoanId == null ? 'bg-base-content/15' : 'bg-transparent'"
              />
            </span>
            <span class="min-w-0 flex-1 truncate text-sm leading-snug">
              <span class="font-medium">{{ t('loans.noBox') }}</span>
              <span class="font-normal opacity-60"> · {{ t('loans.noBoxHint') }}</span>
            </span>
          </button>
        </li>
      </ul>
    </div>
  </details>
</template>
