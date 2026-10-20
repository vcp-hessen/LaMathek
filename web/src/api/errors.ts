import axios from 'axios'

import { errorResponseSchema, type LoanWarning } from './generated/schemas'

export function apiErrorCode(error: unknown): string | null {
  if (
    axios.isAxiosError(error) &&
    error.response?.data &&
    typeof error.response.data === 'object' &&
    'error' in error.response.data
  ) {
    const code = (error.response.data as { error: unknown }).error
    return typeof code === 'string' ? code : null
  }
  return null
}

/** Conflicts attached to a 409 from the availability check. */
export function apiErrorConflicts(error: unknown): LoanWarning[] {
  if (!axios.isAxiosError(error)) return []
  const parsed = errorResponseSchema.safeParse(error.response?.data)
  return parsed.success ? parsed.data.conflicts : []
}
