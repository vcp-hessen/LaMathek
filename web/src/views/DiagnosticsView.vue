<script setup lang="ts">
import { useMe } from '../composables/useMe'
import { useI18n } from 'vue-i18n'
import AuditEventsSection from '../components/AuditEventsSection.vue'
import MailTestPanel from '../components/MailTestPanel.vue'
import FailedMailsSection from '../components/FailedMailsSection.vue'

const { t } = useI18n()

const { data: me, isLoading: meLoading } = useMe()
</script>

<template>
  <div class="app-page space-y-4">
    <h1 class="text-2xl font-bold">{{ t('diagnostics.heading') }}</h1>
    <p v-if="meLoading" class="text-sm">{{ t('auth.loading') }}</p>
    <p v-else-if="!me?.isSuperuser" class="text-sm text-base-content/70">
      {{ t('diagnostics.superuserOnly') }}
    </p>
    <template v-else>
      <p class="text-sm text-base-content/70">{{ t('diagnostics.intro') }}</p>
      <MailTestPanel :default-recipient="me?.email ?? ''" />
      <FailedMailsSection />
      <AuditEventsSection />
    </template>
  </div>
</template>
