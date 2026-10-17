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
  'invalid_loan_state',
  'loan_not_editable',
  'set_already_added',
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

export function useApiErrorMessage() {
  const { t } = useI18n()

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

  return { messageFor }
}
