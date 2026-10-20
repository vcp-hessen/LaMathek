<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useCreateMinimalLoan } from '../composables/useCreateMinimalLoan'

const props = defineProps<{
  open: boolean
  inventoryId: number
  canManage: boolean
}>()

const emit = defineEmits<{ 'update:open': [value: boolean] }>()

const { t } = useI18n()
const router = useRouter()
const { messageFor } = useApiErrorMessage()

// A getter: the active Inventar can change while the palette stays mounted.
const createLoan = useCreateMinimalLoan(() => props.inventoryId)

type CommandId = 'materialType' | 'piece' | 'batch' | 'loan'

const commands = computed(() => {
  if (!props.canManage) return []
  const id = props.inventoryId
  return [
    {
      id: 'materialType' as CommandId,
      label: t('commandPalette.newMaterialType'),
      run: () => router.push({ path: `/inventories/${id}/material-types`, query: { openCreate: '1' } }),
    },
    {
      id: 'piece' as CommandId,
      label: t('commandPalette.newPiece'),
      run: () => router.push({ path: `/inventories/${id}/material`, query: { openCreate: 'piece' } }),
    },
    {
      id: 'batch' as CommandId,
      label: t('commandPalette.newPiecesBatch'),
      run: () => router.push({ path: `/inventories/${id}/material`, query: { openCreate: 'batch' } }),
    },
    {
      id: 'loan' as CommandId,
      label: t('commandPalette.newLoan'),
      run: async () => {
        try {
          const loan = await createLoan.mutateAsync()
          await router.push(`/inventories/${loan.inventoryId}/loans/${loan.id}`)
        } catch (error) {
          runError.value = messageFor(error)
          emit('update:open', true)
        }
      },
    },
  ]
})

const activeIndex = ref(0)
const runError = ref<string | null>(null)

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      activeIndex.value = 0
      if (!runError.value) return
    } else {
      runError.value = null
    }
  },
)

function close() {
  emit('update:open', false)
}

async function runCommand(index: number) {
  const cmd = commands.value[index]
  if (!cmd) return
  close()
  await cmd.run()
}

function onKeydown(event: KeyboardEvent) {
  const mod = event.metaKey || event.ctrlKey
  if (mod && event.key.toLowerCase() === 'k') {
    if (!props.canManage) return
    event.preventDefault()
    emit('update:open', !props.open)
    return
  }
  if (!props.open) return
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
    return
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    activeIndex.value = (activeIndex.value + 1) % Math.max(commands.value.length, 1)
    return
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    const len = commands.value.length
    activeIndex.value = (activeIndex.value - 1 + len) % Math.max(len, 1)
    return
  }
  if (event.key === 'Enter') {
    event.preventDefault()
    void runCommand(activeIndex.value)
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <dialog class="modal" :class="{ 'modal-open': open }" @click.self="close">
    <div class="modal-box max-w-lg p-0">
      <div class="border-b border-base-300 px-4 py-3">
        <p class="text-sm font-medium">{{ t('commandPalette.title') }}</p>
        <p class="text-xs text-base-content/60">{{ t('commandPalette.hint') }}</p>
      </div>
      <p v-if="runError" role="alert" class="px-4 pt-2 text-sm text-error">{{ runError }}</p>
      <ul class="menu p-2">
        <li v-for="(cmd, index) in commands" :key="cmd.id">
          <button
            type="button"
            :class="{ active: index === activeIndex }"
            @click="runCommand(index)"
          >
            {{ cmd.label }}
          </button>
        </li>
      </ul>
      <div class="modal-action px-4 pb-4 pt-0">
        <button type="button" class="btn btn-ghost btn-sm" @click="close">
          {{ t('destructive.cancel') }}
        </button>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop">
      <button type="button" :aria-label="t('destructive.cancel')" @click="close" />
    </form>
  </dialog>
</template>
