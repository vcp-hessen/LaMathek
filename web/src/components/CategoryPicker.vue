<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Category } from '../schemas/material'

const props = defineProps<{
  categories: Category[]
}>()

const categoryText = defineModel<string>({ required: true })

const { t } = useI18n()
const open = ref(false)
const keyboardNav = ref(false)
const activeIndex = ref(0)
const root = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)

const sorted = computed(() =>
  [...props.categories].sort((a, b) => a.name.localeCompare(b.name, 'de')),
)

const filtered = computed(() => {
  const query = categoryText.value.trim().toLocaleLowerCase('de')
  if (!query) return sorted.value
  return sorted.value.filter((category) => category.name.toLocaleLowerCase('de').includes(query))
})

const exactMatch = computed(() =>
  sorted.value.some(
    (category) =>
      category.name.localeCompare(categoryText.value.trim(), 'de', { sensitivity: 'accent' }) === 0,
  ),
)

type MenuItem =
  | { kind: 'clear' }
  | { kind: 'existing'; category: Category }
  | { kind: 'new'; name: string }

const items = computed<MenuItem[]>(() => {
  const list: MenuItem[] = []
  if (categoryText.value.trim()) list.push({ kind: 'clear' })
  for (const category of filtered.value) list.push({ kind: 'existing', category })
  if (categoryText.value.trim() && !exactMatch.value) {
    list.push({ kind: 'new', name: categoryText.value.trim() })
  }
  return list
})

watch(items, (next) => {
  const selected = next.findIndex(
    (item) => item.kind === 'existing' && item.category.name === categoryText.value,
  )
  activeIndex.value = selected >= 0 ? selected : 0
})

function choose(item: MenuItem) {
  if (item.kind === 'clear') categoryText.value = ''
  else if (item.kind === 'existing') categoryText.value = item.category.name
  else categoryText.value = item.name
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
  if (event.key === 'Enter' && open.value && keyboardNav.value && items.value[activeIndex.value]) {
    event.preventDefault()
    choose(items.value[activeIndex.value])
  }
}

function itemLabel(item: MenuItem) {
  if (item.kind === 'clear') return t('material.categoryNone')
  if (item.kind === 'new') return t('material.categoryNew', { name: item.name })
  return item.category.name
}

function isSelected(item: MenuItem) {
  return item.kind === 'existing' && item.category.name === categoryText.value
}
</script>

<template>
  <div ref="root" class="relative w-full">
    <input
      ref="inputRef"
      v-model="categoryText"
      type="text"
      class="input input-bordered w-full pr-10"
      role="combobox"
      :placeholder="t('material.categoryPlaceholder')"
      :aria-expanded="open"
      aria-autocomplete="list"
      aria-controls="category-picker-menu"
      @focus="openMenu"
      @input="onInput"
      @keydown="onKeydown"
    />
    <button
      type="button"
      class="btn btn-ghost btn-sm absolute inset-y-1 right-1 px-2"
      tabindex="-1"
      :aria-label="t('material.categoryMenu')"
      @mousedown.prevent
      @click="toggleMenu"
    >
      <svg viewBox="0 0 20 20" class="size-4 opacity-70" aria-hidden="true">
        <path
          fill="currentColor"
          d="M5.2 7.5a.75.75 0 0 1 1.06 0L10 11.23l3.74-3.73a.75.75 0 1 1 1.06 1.06l-4.27 4.27a.75.75 0 0 1-1.06 0L5.2 8.56a.75.75 0 0 1 0-1.06Z"
        />
      </svg>
    </button>
    <ul
      v-if="open"
      id="category-picker-menu"
      class="menu absolute top-full left-0 z-30 mt-1 max-h-60 w-full! flex-nowrap overflow-y-auto rounded-box border border-base-300 bg-base-100 p-1 shadow-lg"
      role="listbox"
    >
      <li v-if="!items.length" class="menu-disabled">
        <span>{{ t('material.categoryEmpty') }}</span>
      </li>
      <li v-for="(item, index) in items" :key="item.kind === 'existing' ? item.category.id : item.kind">
        <button
          type="button"
          role="option"
          :aria-selected="isSelected(item)"
          :class="{
            'menu-focus': keyboardNav && index === activeIndex,
            'menu-active': isSelected(item),
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
