<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { LoanDetail } from '../../schemas/loan'
import {
  loanPickupInfoSectionOpen,
  loanReturnInfoSectionOpen,
} from '../../utils/loanDetailSectionOpen'
import LoanDetailDisclosure from './LoanDetailDisclosure.vue'
import PhotoGallery from '../PhotoGallery.vue'
import { LOAN_DETAIL_DISCLOSURE_STACK } from './loanDetailLayout'

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
  if (!props.canManage || props.isClosedPhase) return false
  return loanPickupInfoSectionOpen(props.loan.phase)
})

const openReturnSection = computed(() => {
  if (props.isClosedPhase) return false
  return loanReturnInfoSectionOpen(props.loan.phase)
})
</script>

<template>
  <div :class="LOAN_DETAIL_DISCLOSURE_STACK">
    <LoanDetailDisclosure
      :open="openPickupSection"
      :title="t('loans.sectionPickup')"
    >
      <div class="space-y-3">
        <label v-if="canManage" class="flex min-w-0 flex-col gap-1">
          <textarea
            :value="editPickupNote"
            class="textarea textarea-bordered textarea-sm w-full"
            rows="3"
            :aria-label="t('loans.sectionPickup')"
            :placeholder="t('loans.pickupNotePlaceholder')"
            @input="emit('update:editPickupNote', ($event.target as HTMLTextAreaElement).value)"
          />
        </label>
        <p v-else class="whitespace-pre-wrap text-sm">{{ loan.pickupNote || '—' }}</p>
        <PhotoGallery
          :owner="{ kind: 'loan', loanId: loan.id, role: 'pickup' }"
          :photos="loan.pickupPhotos ?? []"
          :readonly="!canManage || isClosedPhase"
          @change="emit('photosChange')"
        >
          <template v-if="canManage" #toolbarTrailing>
            <button
              type="button"
              class="btn btn-primary btn-sm shrink-0"
              :disabled="patchPending"
              @click="emit('savePickupNote')"
            >
              {{ t('material.save') }}
            </button>
          </template>
        </PhotoGallery>
      </div>
    </LoanDetailDisclosure>

    <LoanDetailDisclosure
      :open="openReturnSection"
      :title="t('loans.sectionReturn')"
    >
      <div class="space-y-3">
        <label
          v-if="canParticipateInLineWorkflow && !isClosedPhase"
          class="flex min-w-0 flex-col gap-1"
        >
          <textarea
            :value="editReturnNote"
            class="textarea textarea-bordered textarea-sm w-full"
            rows="3"
            :aria-label="t('loans.sectionReturn')"
            :placeholder="t('loans.returnNotePlaceholder')"
            @input="emit('update:editReturnNote', ($event.target as HTMLTextAreaElement).value)"
          />
        </label>
        <p v-else class="whitespace-pre-wrap text-sm">{{ loan.returnNote || '—' }}</p>
        <PhotoGallery
          :owner="{ kind: 'loan', loanId: loan.id, role: 'return' }"
          :photos="loan.returnPhotos ?? []"
          :readonly="isClosedPhase || !canParticipateInLineWorkflow"
          @change="emit('photosChange')"
        >
          <template
            v-if="canParticipateInLineWorkflow && !isClosedPhase"
            #toolbarTrailing
          >
            <button
              type="button"
              class="btn btn-primary btn-sm shrink-0"
              :disabled="patchPending"
              @click="emit('saveReturnNote')"
            >
              {{ t('material.save') }}
            </button>
          </template>
        </PhotoGallery>
      </div>
    </LoanDetailDisclosure>
  </div>
</template>
