<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

defineProps<{
  warning: string
  title?: string
  label?: string
  disabled?: boolean
}>()

const emit = defineEmits<{ confirmed: [] }>()

const { t } = useI18n()
const dialogRef = ref<HTMLDialogElement | null>(null)

function openDialog() {
  dialogRef.value?.showModal()
}

function confirm() {
  dialogRef.value?.close()
  emit('confirmed')
}
</script>

<template>
  <button
    type="button"
    class="btn btn-ghost btn-sm text-error"
    :disabled="disabled"
    @click="openDialog"
  >
    {{ label ?? t('destructive.delete') }}
  </button>
  <dialog ref="dialogRef" class="modal">
    <div class="modal-box max-w-lg text-left">
      <h3 class="text-lg font-bold">{{ title ?? t('destructive.deleteTitle') }}</h3>
      <p class="py-4 text-sm whitespace-pre-wrap">{{ warning }}</p>
      <div class="modal-action">
        <form method="dialog">
          <button type="submit" class="btn btn-ghost">{{ t('destructive.cancel') }}</button>
        </form>
        <button type="button" class="btn btn-error" @click="confirm">
          {{ t('destructive.confirmDelete') }}
        </button>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop">
      <button type="submit">{{ t('destructive.cancel') }}</button>
    </form>
  </dialog>
</template>
