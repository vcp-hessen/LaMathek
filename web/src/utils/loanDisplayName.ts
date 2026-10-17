/** What users recognize first: Veranstaltung/Titel, then Gruppe. */
export function loanDisplayName(loan: {
  groupName: string
  eventName?: string | null
}): string {
  const title = loan.eventName?.trim()
  if (title) return title
  const group = loan.groupName.trim()
  if (group && group !== '—') return group
  return ''
}
