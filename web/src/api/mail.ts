import { z } from 'zod'
import { api } from './client'

const mailStatusSchema = z.object({
  configured: z.boolean(),
  host: z.string(),
  port: z.number(),
  fromAddress: z.string(),
  mode: z.string(),
  hasCredentials: z.boolean(),
})

const mailTestStartSchema = z.object({
  id: z.string(),
})

const mailTestJobSchema = z.object({
  status: z.enum(['pending', 'sent', 'failed']),
  detail: z.string().optional(),
})

export type MailStatus = z.infer<typeof mailStatusSchema>
export type MailTestJob = z.infer<typeof mailTestJobSchema>

export async function fetchMailStatus(): Promise<MailStatus> {
  const response = await api.get('/api/mail/status')
  return mailStatusSchema.parse(response.data)
}

export async function startMailTest(to: string): Promise<string> {
  const response = await api.post('/api/mail/test', { to }, { validateStatus: (s) => s === 202 })
  return mailTestStartSchema.parse(response.data).id
}

export async function fetchMailTestJob(id: string): Promise<MailTestJob> {
  const response = await api.get(`/api/mail/test/${id}`)
  return mailTestJobSchema.parse(response.data)
}
