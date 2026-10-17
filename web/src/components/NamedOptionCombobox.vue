<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'

export type NamedOption = { id: number; name: string }

const props = withDefaults(
  defineProps<{
    options: NamedOption[]
    placeholder: string
    clearLabelKey: string
    emptyLabelKey: string
    menuLabelKey: string
    newLabelKey: string
    inputSize?: 'sm' | 'md'
    required?: boolean
  }>(),
  { inputSize: 'md', required: false },
)

const text = defineModel<string>({ required: true })

const { t } = useI18n()
const menuId = useId()
const open = ref(false)
const keyboardNav = ref(false)
const activeIndex = ref(0)
const root = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)

const sorted = computed(() =>
  [...props.options].sort((a, b) => a.name.localeCompare(b.name, 'de')),
)

const filtered = computed(() => {
  const query = text.value.trim().toLocaleLowerCase('de')
  if (!query) return sorted.value
  return sorted.value.filter((row) => row.name.toLocaleLowerCase('de').includes(query))
})

const exactMatch = computed(() =>
  sorted.value.some(
    (row) => row.name.localeCompare(text.value.trim(), 'de', { sensitivity: 'accent' }) === 0,
  ),
)

type MenuItem =
  | { kind: 'clear' }
  | { kind: 'existing'; option: NamedOption }
  | { kind: 'new'; name: string }

const items = computed<MenuItem[]>(() => {
  const list: MenuItem[] = []
  if (text.value.trim()) list.push({ kind: 'clear' })
  for (const option of filtered.value) list.push({ kind: 'existing', option })
  if (text.value.trim() && !exactMatch.value) {
    list.push({ kind: 'new', name: text.value.trim() })
  }
  return list
})

const fieldClass = computed(() =>
  [
    'select select-bordered w-full min-w-0',
    props.inputSize === 'sm' ? 'select-sm' : '',
  ].join(' '),
)

watch(items, (next) => {
  const selected = next.findIndex(
    (item) => item.kind === 'existing' && item.option.name === text.value,
  )
  activeIndex.value = selected >= 0 ? selected : 0
})

function choose(item: MenuItem) {
  if (item.kind === 'clear') text.value = ''
  else if (item.kind === 'existing') text.value = item.option.name
  else text.value = item.name
  open.value = false
  keyboardNav.value = false
}

function confirmFromKeyboard() {
  const trimmed = text.value.trim()
  if (!trimmed) {
    open.value = false
    keyboardNav.value = false
    return
  }
  if (keyboardNav.value && items.value[activeIndex.value]) {
    choose(items.value[activeIndex.value])
    return
  }
  const canonical = sorted.value.find(
    (row) => row.name.localeCompare(trimmed, 'de', { sensitivity: 'accent' }) === 0,
  )
  if (canonical) {
    text.value = canonical.name
    open.value = false
    keyboardNav.value = false
    return
  }
  const newItem = items.value.find((item) => item.kind === 'new')
  if (newItem) {
    choose(newItem)
    return
  }
  const existingOnly = items.value.filter((item) => item.kind === 'existing')
  if (existingOnly.length === 1) {
    choose(existingOnly[0])
    return
  }
  text.value = trimmed
  open.value = false
  keyboardNav.value = false
}

function onDocumentPointerDown(event: PointerEvent) {
  if (!open.value) return
  const target = event.target as Node
  if (root.value?.contains(target)) return
  open.value = false
  keyboardNav.value = false
}

onMounted(() => document.addEventListener('pointerdown', onDocumentPointerDown))
onUnmounted(() => document.removeEventListener('pointerdown', onDocumentPointerDown))

function openMenu() {
  open.value = true
}

function toggleMenu() {
  open.value = !open.value
  if (open.value) inputRef.value?.focus()
}

function onInput() {
  open.value = true
  keyboardNav.value = false
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    open.value = false
    keyboardNav.value = false
    return
  }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    if (!items.value.length) return
    if (!open.value) {
      open.value = true
      keyboardNav.value = true
      return
    }
    keyboardNav.value = true
    const step = event.key === 'ArrowDown' ? 1 : -1
    activeIndex.value = (activeIndex.value + step + items.value.length) % items.value.length
    return
  }
  if (event.key === 'Enter') {
    event.preventDefault()
    confirmFromKeyboard()
  }
}

function itemLabel(item: MenuItem) {
  if (item.kind === 'clear') return t(props.clearLabelKey)
  if (item.kind === 'new') return t(props.newLabelKey, { name: item.name })
  return item.option.name
}

function isSelected(item: MenuItem) {
  return item.kind === 'existing' && item.option.name === text.value
}
</script>

<template>
  <div ref="root" class="relative w-full min-w-0">
    <div :class="fieldClass">
      <input
        ref="inputRef"
        v-model="text"
        type="text"
        class="grow min-w-0 bg-transparent outline-none"
        role="combobox"
        :placeholder="placeholder"
        :required="required"
        :aria-expanded="open"
        aria-autocomplete="list"
        :aria-controls="menuId"
        @focus="openMenu"
        @input="onInput"
        @keydown="onKeydown"
      />
      <button
        type="button"
        class="flex shrink-0 items-center self-stretch px-1"
        tabindex="-1"
        :aria-label="t(menuLabelKey)"
        @mousedown.prevent
        @click="toggleMenu"
      >
        <span class="sr-only">{{ t(menuLabelKey) }}</span>
      </button>
    </div>
    <ul
      v-if="open"
      :id="menuId"
      class="menu menu-sm absolute top-full left-0 z-30 mt-1 max-h-60 w-full overflow-y-auto rounded-box border border-base-200 bg-base-100 p-1 shadow-lg"
      role="listbox"
    >
      <li v-if="!items.length" class="disabled">
        <span class="text-sm opacity-70">{{ t(emptyLabelKey) }}</span>
      </li>
      <li v-for="(item, index) in items" :key="item.kind === 'existing' ? item.option.id : `${item.kind}-${index}`">
        <button
          type="button"
          role="option"
          :aria-selected="isSelected(item)"
          :class="{
            'active': keyboardNav && index === activeIndex,
            'font-medium': isSelected(item),
          }"
          @mouseenter="activeIndex = index"
          @click="choose(item)"
        >
          {{ itemLabel(item) }}
        </button>
      </li>
    </ul>
  </div>
</template>
