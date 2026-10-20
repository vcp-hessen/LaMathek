import { mount } from '@vue/test-utils'
import { AxiosError, AxiosHeaders } from 'axios'
import { describe, expect, it } from 'vitest'
import { defineComponent } from 'vue'
import { createI18n } from 'vue-i18n'

import de from '../locales/de.json'
import type { LoanWarning } from '../schemas/loan'
import { useApiErrorMessage } from './useApiErrorMessage'

/** A conflict as the API sends it: every key, null where it does not apply. */
function conflict(fields: Partial<LoanWarning> & { code: string }): LoanWarning {
  return {
    lineId: null,
    pieceId: null,
    materialTypeId: null,
    otherLoanId: null,
    otherLoanTitle: null,
    otherInventoryId: null,
    itemLabel: null,
    available: null,
    occupied: null,
    requested: null,
    ...fields,
  }
}

function apiError(status: number, data: unknown): AxiosError {
  const config = { headers: new AxiosHeaders() }
  return new AxiosError('failed', 'ERR', config, null, {
    status,
    statusText: '',
    headers: {},
    config,
    data,
  })
}

function withComposable() {
  let api!: ReturnType<typeof useApiErrorMessage>
  const Probe = defineComponent({
    setup() {
      api = useApiErrorMessage()
      return () => null
    },
  })
  mount(Probe, { global: { plugins: [createI18n({ legacy: false, locale: 'de', messages: { de } })] } })
  return api
}

describe('useApiErrorMessage', () => {
  it('finds texts in every error namespace and falls back to the code', () => {
    const { messageFor } = withComposable()
    expect(messageFor(apiError(409, { error: 'email_taken' }))).toBe(de.errors.email_taken)
    expect(messageFor(apiError(400, { error: 'pickup_required' }))).toBe(de.loans.errors.pickup_required)
    expect(messageFor(apiError(400, { error: 'something_new' }))).toContain('something_new')
  })

  it('lists availability conflicts with the item and the other loan', () => {
    const { loanActionMessageFor } = withComposable()
    const message = loanActionMessageFor(
      apiError(409, {
        error: 'over_loaned',
        conflicts: [
          conflict({ code: 'stock_short', itemLabel: '12 × Seil (3 m)', available: 20, occupied: 12, requested: 12 }),
          conflict({ code: 'piece_booked', itemLabel: 'HD 1', otherLoanId: 4, otherLoanTitle: 'Herbstfahrt' }),
        ],
      }),
    )
    expect(message.split('\n')).toEqual([
      de.loans.errors.over_loaned,
      '• 12 × Seil (3 m): nur 8 von 20 frei im Zeitraum, 12 gewünscht',
      '• HD 1: im Zeitraum schon vergeben an „Herbstfahrt“',
    ])
  })
})
