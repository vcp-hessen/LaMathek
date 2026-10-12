import { api } from './client'
import { auditEventSchema, type AuditEvent } from '../schemas/audit'

export async function fetchAuditEvents(): Promise<AuditEvent[]> {
  const response = await api.get('/api/audit-events')
  return auditEventSchema.array().parse(response.data)
}
