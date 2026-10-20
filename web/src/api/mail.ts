import { api } from './client'
import {
  mailStatusSchema,
  mailTestJobSchema,
  mailTestStartedSchema,
  outboxMailSchema,
  type MailStatus,
  type MailTestJob,
  type OutboxMail,
} from './generated/schemas'

export type { MailStatus, MailTestJob }

export async function fetchMailStatus(): Promise<MailStatus> {
  const response = await api.get('/api/mail/status')
  return mailStatusSchema.parse(response.data)
}

export async function startMailTest(to: string): Promise<string> {
  const response = await api.post('/api/mail/test', { to }, { validateStatus: (s) => s === 202 })
  return mailTestStartedSchema.parse(response.data).id
}

export async function fetchMailTestJob(id: string): Promise<MailTestJob> {
  const response = await api.get(`/api/mail/test/${id}`)
  return mailTestJobSchema.parse(response.data)
}

/** Mails that gave up after all retries (superusers). */
export async function fetchFailedOutbox(): Promise<OutboxMail[]> {
  const response = await api.get('/api/mail/outbox')
  return outboxMailSchema.array().parse(response.data)
}
