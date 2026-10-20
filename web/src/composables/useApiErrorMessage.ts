import { useI18n } from 'vue-i18n'
import { apiErrorCode, apiErrorConflicts } from '../api/errors'
import type { LoanWarning } from '../schemas/loan'

export type BoxActionErrorFeedback = {
  hint: string
  banner: string
}

export function useApiErrorMessage() {
  const { t, te } = useI18n()

  /** First match of `errors.*`, `loans.errors.*`, `material.errors.*`; else a generic text. */
  function textFor(code: string | null): string {
    if (code) {
      for (const ns of ['errors', 'loans.errors', 'material.errors']) {
        if (te(`${ns}.${code}`)) return t(`${ns}.${code}`)
      }
    }
    return t('material.errors.generic', { code: code ?? 'unknown' })
  }

  function loanErrorText(code: string): string {
    return t(`loans.errors.${code}`)
  }

  /** One line per conflict, e.g. "Kohte 1: im Zeitraum schon vergeben an „Stamm A“". */
  function conflictText(warning: LoanWarning): string {
    const available = warning.available ?? 0
    const other = warning.otherLoanTitle
      ? `„${warning.otherLoanTitle}“`
      : t('loans.warnings.unknownLoan')
    const text = t(`loans.warnings.${warning.code}`, {
      other,
      available,
      free: Math.max(0, available - (warning.occupied ?? 0)),
      requested: warning.requested ?? 0,
    })
    return warning.itemLabel ? `${warning.itemLabel}: ${text}` : text
  }

  /** The error text, followed by the conflicts the server named (if any). */
  function withConflicts(message: string, error: unknown): string {
    const conflicts = apiErrorConflicts(error)
    if (!conflicts.length) return message
    return [message, ...conflicts.map((c) => `• ${conflictText(c)}`)].join('\n')
  }

  function boxActionFeedback(error: unknown): BoxActionErrorFeedback {
    const code = apiErrorCode(error)
    if (code === 'piece_unavailable') {
      return {
        hint: loanErrorText('piece_unavailable'),
        banner: withConflicts(t('loans.errors.piece_unavailable_detail'), error),
      }
    }
    const message = textFor(code)
    return { hint: message, banner: withConflicts(message, error) }
  }

  function loanActionMessageFor(error: unknown): string {
    const code = apiErrorCode(error)
    if (code === 'piece_unavailable' && !apiErrorConflicts(error).length) {
      return t('loans.errors.piece_unavailable_detail')
    }
    return withConflicts(messageFor(error), error)
  }

  function messageFor(error: unknown): string {
    return textFor(apiErrorCode(error))
  }

  return { messageFor, loanActionMessageFor, boxActionFeedback, conflictText }
}
