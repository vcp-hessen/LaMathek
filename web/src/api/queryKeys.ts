/**
 * All TanStack Query keys in one place. Nested keys (e.g. a loan's journal under
 * `loan(id)`) are invalidated together with their parent.
 */
export const queryKeys = {
  me: ['me'] as const,
  authMode: ['authMode'] as const,
  settings: ['settings'] as const,
  dashboard: ['dashboard'] as const,
  inventories: ['inventories'] as const,
  users: ['users'] as const,
  borrowers: ['borrowers'] as const,
  categories: ['categories'] as const,
  groups: ['groups'] as const,
  myLoans: ['my-loans'] as const,
  auditEvents: ['audit-events'] as const,
  calendarFeeds: ['calendar-feeds'] as const,
  failedMails: ['mail-outbox-failed'] as const,
}
