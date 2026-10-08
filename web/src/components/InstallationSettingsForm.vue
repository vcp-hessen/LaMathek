<script setup lang="ts">
import { toTypedSchema } from '@vee-validate/zod'
import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { useForm } from 'vee-validate'
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { z } from 'zod'
import { updateInstallationSettings } from '../api/settings'
import type { InstallationSettings } from '../schemas/settings'

const props = defineProps<{
  settings: InstallationSettings
}>()

const { t } = useI18n()
const queryClient = useQueryClient()

const schema = toTypedSchema(
  z.object({
    title: z.string().min(1),
    subtitle: z.string().min(1),
  }),
)

const { defineField, handleSubmit, isSubmitting, resetForm } = useForm({
  validationSchema: schema,
  initialValues: {
    title: props.settings.title,
    subtitle: props.settings.subtitle,
  },
})

const [title] = defineField('title')
const [subtitle] = defineField('subtitle')

watch(
  () => props.settings,
  (settings) => {
    resetForm({
      values: { title: settings.title, subtitle: settings.subtitle },
    })
  },
)

const mutation = useMutation({
  mutationFn: updateInstallationSettings,
  onSuccess: async () => {
    await queryClient.invalidateQueries({ queryKey: ['settings'] })
  },
})

const onSubmit = handleSubmit(async (values) => {
  await mutation.mutateAsync(values)
  resetForm({ values })
})
</script>

<template>
  <form class="card bg-base-100 shadow-md" @submit="onSubmit">
    <div class="card-body gap-4 text-left">
      <h2 class="card-title text-lg">{{ t('settings.heading') }}</h2>
      <label class="form-control w-full">
        <span class="label-text">{{ t('settings.titleLabel') }}</span>
        <input v-model="title" type="text" class="input input-bordered w-full" />
      </label>
      <label class="form-control w-full">
        <span class="label-text">{{ t('settings.subtitleLabel') }}</span>
        <input v-model="subtitle" type="text" class="input input-bordered w-full" />
      </label>
      <p v-if="mutation.isError.value" class="text-sm text-error">
        {{ t('settings.saveFailed') }}
      </p>
      <div class="card-actions justify-end">
        <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
          {{ t('settings.save') }}
        </button>
      </div>
    </div>
  </form>
</template>
