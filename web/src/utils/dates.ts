/** Date helpers for API values: dates are "YYYY-MM-DD", timestamps ISO with offset. */

const LOCALE = 'de-DE'

/** Today (or ``date``) as "YYYY-MM-DD" in the browser's time zone, not UTC. */
export function localIsoDate(date: Date = new Date()): string {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

/** "2026-10-20" → "20.10.2026"; empty → "—". Parsed as a local date, never shifted. */
export function formatDate(value: string | null | undefined): string {
  if (!value?.trim()) return '—'
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  if (!year || !month || !day) return value
  return new Date(year, month - 1, day).toLocaleDateString(LOCALE, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

/** ISO timestamp → "20.10.26, 11:15" in the browser's time zone; empty → "". */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(LOCALE, { dateStyle: 'short', timeStyle: 'short' })
}
