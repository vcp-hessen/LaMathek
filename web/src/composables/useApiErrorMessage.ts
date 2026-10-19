import { useI18n } from 'vue-i18n'
import { apiErrorCode, apiErrorConflicts } from '../api/errors'
import type { LoanWarning } from '../schemas/loan'

const LOAN_ERROR_CODES = new Set([
  'pickup_required',
  'return_required',
  'invalid_date_range',
  'invalid_permanent_fields',
  'invalid_contact',
  'contact_required',
  'empty_loan',
  'borrower_phone_required',
  'piece_unavailable',
  'over_loaned',
  'line_exists',
  'set_unavailable',
  'invalid_line_status',
  'workflow_step_mismatch',
  'invalid_loan_state',
  'loan_not_editable',
  'set_already_added',
  'mail_not_sent',
  'step_incomplete',
  'dates_conflict',
  'reason_required',
])

const KNOWN_CODES = new Set([
  'tracking_locked',
  'material_type_locked',
  'piece_has_history',
  'material_type_not_empty',
  'below_loaned',
  'name_taken',
  'invalid_variants',
  'duplicate_variant_label',
  'invalid_variant',
  'piece_on_other_set',
  'short_name_taken',
  'unit_not_for_piece',
  'invalid_category',
  'invalid_coordinates',
  'invalid_visibility',
  'invalid_field',
  'invalid_count',
  'invalid_name_pattern',
  'invalid_set',
  'set_conflict',
  'invalid_acquired_year',
  'invalid_new_value',
  'invalid_status',
])

export type BoxActionErrorFeedback = {
  hint: string
  banner: string
}

export function useApiErrorMessage() {
  const { t } = useI18n()

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
    if (code && LOAN_ERROR_CODES.has(code)) {
      const message = loanErrorText(code)
      return { hint: message, banner: message }
    }
    if (code && KNOWN_CODES.has(code)) {
      const message = t(`material.errors.${code}`)
      return { hint: message, banner: message }
    }
    const generic = code
      ? t('material.errors.generic', { code })
      : t('material.errors.generic', { code: 'unknown' })
    return { hint: generic, banner: generic }
  }

  function loanActionMessageFor(error: unknown): string {
    const code = apiErrorCode(error)
    if (code === 'piece_unavailable' && !apiErrorConflicts(error).length) {
      return t('loans.errors.piece_unavailable_detail')
    }
    return withConflicts(messageFor(error), error)
  }

  function messageFor(error: unknown): string {
    const code = apiErrorCode(error)
    if (code && LOAN_ERROR_CODES.has(code)) {
      return t(`loans.errors.${code}`)
    }
    if (code && KNOWN_CODES.has(code)) {
      return t(`material.errors.${code}`)
    }
    if (code) {
      return t('material.errors.generic', { code })
    }
    return t('material.errors.generic', { code: 'unknown' })
  }

  return { messageFor, loanActionMessageFor, boxActionFeedback, conflictText }
}
