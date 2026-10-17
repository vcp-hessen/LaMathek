<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { LoanDetail } from '../../schemas/loan'
import PhotoGallery from '../PhotoGallery.vue'
import { LOAN_DETAIL_SECTION } from './loanDetailLayout'

const props = defineProps<{
  loan: LoanDetail
  canManage: boolean
  isLoanBorrower: boolean
  canParticipateInLineWorkflow: boolean
  isClosedPhase: boolean
  isPermanent: boolean
  editPickupNote: string
  editReturnNote: string
  patchPending: boolean
}>()

const emit = defineEmits<{
  'update:editPickupNote': [value: string]
  'update:editReturnNote': [value: string]
  savePickupNote: []
  saveReturnNote: []
  photosChange: []
}>()

const { t } = useI18n()

const openPickupSection = computed(() => {
  if (props.isClosedPhase) return false
  return props.canManage && props.loan.phase === 'active'
})

const openReturnSection = computed(() => !props.isClosedPhase)
</script>

<template>
  <section :class="LOAN_DETAIL_SECTION">
    <h2 class="app-page-title text-base">{{ t('loans.sectionPhotos') }}</h2>
    <PhotoGallery
      :owner="{ kind: 'loan', loanId: loan.id }"
      :photos="loan.photos ?? []"
      :readonly="isClosedPhase"
      @change="emit('photosChange')"
    />
  </section>

  <section :class="LOAN_DETAIL_SECTION">
    <details class="group" :open="openPickupSection">
      <summary
        class="app-page-title cursor-pointer text-base list-none [&::-webkit-details-marker]:hidden"
      >
        {{ t('loans.sectionPickup') }}
      </summary>
      <div class="mt-3 space-y-3">
        <label v-if="canManage" class="flex min-w-0 flex-col gap-1">
          <span class="text-xs opacity-80">{{ t('loans.pickupNoteHeading') }}</span>
          <textarea
            :value="editPickupNote"
            class="textarea textarea-bordered textarea-sm w-full"
            rows="3"
            @input="emit('update:editPickupNote', ($event.target as HTMLTextAreaElement).value)"
          />
        </label>
        <p v-else class="whitespace-pre-wrap text-sm">{{ loan.pickupNote || '—' }}</p>
        <div v-if="canManage" class="flex justify-end">
          <button
            type="button"
            class="btn btn-primary btn-sm"
            :disabled="patchPending"
            @click="emit('savePickupNote')"
          >
            {{ t('material.save') }}
          </button>
        </div>
        <PhotoGallery
          :owner="{ kind: 'loan', loanId: loan.id, role: 'pickup' }"
          :photos="loan.pickupPhotos ?? []"
          :readonly="!canManage || isClosedPhase"
          @change="emit('photosChange')"
        />
      </div>
    </details>
  </section>

  <section :class="LOAN_DETAIL_SECTION">
    <details class="group" :open="openReturnSection">
      <summary
        class="app-page-title cursor-pointer text-base list-none [&::-webkit-details-marker]:hidden"
      >
        {{ t('loans.sectionReturn') }}
      </summary>
      <div class="mt-3 space-y-3">
        <label
          v-if="canParticipateInLineWorkflow && !isClosedPhase"
          class="flex min-w-0 flex-col gap-1"
        >
          <span class="text-xs opacity-80">{{ t('loans.returnNoteHeading') }}</span>
          <textarea
            :value="editReturnNote"
            class="textarea textarea-bordered textarea-sm w-full"
            rows="3"
            @input="emit('update:editReturnNote', ($event.target as HTMLTextAreaElement).value)"
          />
        </label>
        <p v-else class="whitespace-pre-wrap text-sm">{{ loan.returnNote || '—' }}</p>
        <div v-if="canParticipateInLineWorkflow && !isClosedPhase" class="flex justify-end">
          <button
            type="button"
            class="btn btn-primary btn-sm"
            :disabled="patchPending"
            @click="emit('saveReturnNote')"
          >
            {{ t('material.save') }}
          </button>
        </div>
        <PhotoGallery
          :owner="{ kind: 'loan', loanId: loan.id, role: 'return' }"
          :photos="loan.returnPhotos ?? []"
          :readonly="isClosedPhase || !canParticipateInLineWorkflow"
          @change="emit('photosChange')"
        />
      </div>
    </details>
  </section>
</template>
