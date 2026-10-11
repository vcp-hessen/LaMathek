import { useI18n } from 'vue-i18n'
import { apiErrorCode } from '../api/errors'

const KNOWN_CODES = new Set([
  'tracking_locked',
  'material_type_locked',
  'piece_on_loan',
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
  'invalid_field',
  'invalid_count',
  'invalid_name_pattern',
  'invalid_set',
  'set_conflict',
])

export function useApiErrorMessage() {
  const { t } = useI18n()

  function messageFor(error: unknown): string {
    const code = apiErrorCode(error)
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
