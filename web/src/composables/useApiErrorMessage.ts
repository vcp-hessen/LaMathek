import { useI18n } from 'vue-i18n'
import { apiErrorCode } from '../api/errors'

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
])

const KNOWN_CODES = new Set([
  'tracking_locked',
  'material_type_locked',
  'piece_on_loan',
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

  function boxActionFeedback(error: unknown): BoxActionErrorFeedback {
    const code = apiErrorCode(error)
    if (code === 'piece_unavailable') {
      return {
        hint: loanErrorText('piece_unavailable'),
        banner: t('loans.errors.piece_unavailable_detail'),
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
    if (code === 'piece_unavailable') {
      return t('loans.errors.piece_unavailable_detail')
    }
    return messageFor(error)
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

  return { messageFor, loanActionMessageFor, boxActionFeedback }
}
