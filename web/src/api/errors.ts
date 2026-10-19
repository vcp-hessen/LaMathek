import axios from 'axios'
import { z } from 'zod'

import { loanWarningSchema, type LoanWarning } from '../schemas/loan'

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
  const data = error.response?.data as { conflicts?: unknown } | undefined
  const parsed = z.array(loanWarningSchema).safeParse(data?.conflicts)
  return parsed.success ? parsed.data : []
}
