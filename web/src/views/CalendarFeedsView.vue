<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  createCalendarFeed,
  deleteCalendarFeed,
  fetchCalendarFeeds,
  type CalendarFeed,
  type CalendarFeedScope,
} from '../api/calendarFeeds'
import { fetchInventories } from '../api/inventories'
import { fetchMe } from '../api/me'
import { calendarInventoryLabel } from '../utils/calendarContent'

type ContentOption = {
  key: string
  scope: CalendarFeedScope
  inventoryId?: number
  label: string
}

const { t } = useI18n()
const queryClient = useQueryClient()

const label = ref('')
const contentKey = ref('borrower')
const createdUrl = ref<string | null>(null)
const copyDone = ref(false)
const formError = ref<string | null>(null)

const { data: me } = useQuery({ queryKey: ['me'], queryFn: fetchMe })

const { data: inventories } = useQuery({
  queryKey: ['inventories'],
  queryFn: fetchInventories,
  enabled: () => !!me.value,
})

const contentOptions = computed((): ContentOption[] => {
  const options: ContentOption[] = [
    {
      key: 'borrower',
      scope: 'borrower',
      label: t('calendar.contentBorrower'),
    },
  ]
  for (const inventory of inventories.value ?? []) {
    options.push({
      key: `contact:${inventory.id}`,
      scope: 'contact',
      inventoryId: inventory.id,
      label: calendarInventoryLabel(t, inventory.name, 'contact'),
    })
    if (inventory.canManage) {
      options.push({
        key: `inventory:${inventory.id}`,
        scope: 'inventory',
        inventoryId: inventory.id,
        label: calendarInventoryLabel(t, inventory.name, 'all'),
      })
    }
  }
  return options
})

const selectedContent = computed(() =>
  contentOptions.value.find((option) => option.key === contentKey.value),
)

watch(
  contentOptions,
  (options) => {
    if (!options.some((option) => option.key === contentKey.value)) {
      contentKey.value = options[0]?.key ?? 'borrower'
    }
  },
  { immediate: true },
)

const { data: feeds, isLoading } = useQuery({
  queryKey: ['calendar-feeds'],
  queryFn: fetchCalendarFeeds,
  enabled: () => !!me.value,
})

const createMutation = useMutation({
  mutationFn: createCalendarFeed,
  onSuccess: (created) => {
    createdUrl.value = `${window.location.origin}${created.path}`
    label.value = ''
    formError.value = null
    void queryClient.invalidateQueries({ queryKey: ['calendar-feeds'] })
  },
  onError: () => {
    formError.value = t('calendar.feedsCreateFailed')
  },
})

const deleteMutation = useMutation({
  mutationFn: deleteCalendarFeed,
  onSuccess: async () => {
    await queryClient.invalidateQueries({ queryKey: ['calendar-feeds'] })
  },
})

function feedContentLabel(feed: CalendarFeed): string {
  if (feed.scope === 'borrower') {
    return t('calendar.contentBorrower')
  }
  if (feed.scope === 'contact') {
    return calendarInventoryLabel(t, feed.inventoryName, 'contact')
  }
  return calendarInventoryLabel(t, feed.inventoryName, 'all')
}

async function copyCreatedUrl() {
  if (!createdUrl.value) return
  try {
    await navigator.clipboard.writeText(createdUrl.value)
    copyDone.value = true
    window.setTimeout(() => {
      copyDone.value = false
    }, 2000)
  } catch {
    formError.value = t('calendar.feedsCopyFailed')
  }
}

async function onCreate() {
  formError.value = null
  createdUrl.value = null
  copyDone.value = false
  const trimmed = label.value.trim()
  if (!trimmed) {
    formError.value = t('calendar.feedsLabelRequired')
    return
  }
  const content = selectedContent.value
  if (!content) {
    formError.value = t('calendar.feedsCreateFailed')
    return
  }
  await createMutation.mutateAsync({
    label: trimmed,
    scope: content.scope,
    inventoryId: content.inventoryId,
  })
}

function onDelete(feed: CalendarFeed) {
  if (!window.confirm(t('calendar.feedsDeleteConfirm', { label: feed.label }))) {
    return
  }
  deleteMutation.mutate(feed.id)
}
</script>

<template>
  <div class="app-page">
    <h1 class="text-2xl font-semibold">{{ t('calendar.feedsHeading') }}</h1>
    <p class="mt-2 max-w-3xl text-sm text-base-content/70">{{ t('calendar.feedsIntro') }}</p>

    <p v-if="!me" class="mt-4 text-sm">
      {{ t('calendar.hubSignIn') }}
      <a class="link" href="/login">{{ t('auth.signIn') }}</a>
    </p>

    <template v-else>
      <form class="mt-6 max-w-3xl space-y-3 rounded-lg border border-base-300 p-4" @submit.prevent="onCreate">
        <h2 class="text-sm font-medium">{{ t('calendar.feedsCreateHeading') }}</h2>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label class="flex min-w-0 flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('calendar.feedsLabel') }}</span>
            <input
              v-model="label"
              type="text"
              class="input input-bordered input-sm w-full"
              :placeholder="t('calendar.feedsLabelPlaceholder')"
              maxlength="255"
            />
          </label>
          <label class="flex min-w-0 flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('calendar.feedsScope') }}</span>
            <select v-model="contentKey" class="select select-bordered select-sm w-full">
              <option v-for="option in contentOptions" :key="option.key" :value="option.key">
                {{ option.label }}
              </option>
            </select>
          </label>
        </div>
        <p v-if="formError" class="text-sm text-error">{{ formError }}</p>
        <button
          type="submit"
          class="btn btn-primary btn-sm"
          :disabled="createMutation.isPending.value || contentOptions.length === 0"
        >
          {{ t('calendar.feedsCreate') }}
        </button>
        <div v-if="createdUrl" class="space-y-1 pt-1">
          <p class="text-xs text-base-content/70">{{ t('calendar.feedsCreatedHint') }}</p>
          <div class="join flex w-full">
            <input
              :value="createdUrl"
              type="text"
              readonly
              class="input input-bordered input-sm join-item min-w-0 flex-1 font-mono text-xs"
              :aria-label="t('calendar.feedsUrlLabel')"
            />
            <button
              type="button"
              class="btn btn-outline btn-sm join-item shrink-0"
              @click="copyCreatedUrl"
            >
              {{ copyDone ? t('calendar.feedsCopied') : t('calendar.feedsCopy') }}
            </button>
          </div>
        </div>
      </form>

      <section class="mt-8 max-w-3xl">
        <h2 class="text-sm font-medium">{{ t('calendar.feedsListHeading') }}</h2>
        <p v-if="isLoading" class="mt-2 text-sm">{{ t('auth.loading') }}</p>
        <p v-else-if="!feeds?.length" class="mt-2 text-sm text-base-content/70">
          {{ t('calendar.feedsEmpty') }}
        </p>
        <ul v-else class="mt-3 divide-y divide-base-300 rounded-lg border border-base-300">
          <li
            v-for="feed in feeds"
            :key="feed.id"
            class="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm"
          >
            <div class="min-w-0">
              <p class="font-medium">{{ feed.label }}</p>
              <p class="text-xs text-base-content/70">
                {{ feedContentLabel(feed) }}
                <span v-if="feed.createdAt"> · {{ feed.createdAt.slice(0, 10) }}</span>
              </p>
            </div>
            <button
              type="button"
              class="btn btn-ghost btn-sm text-error"
              :disabled="deleteMutation.isPending.value"
              @click="onDelete(feed)"
            >
              {{ t('calendar.feedsDelete') }}
            </button>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
