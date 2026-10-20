import { describe, expect, it } from 'vitest'

import { easterSunday, isoDate, publicHolidays } from './germanPublicHolidays'

describe('publicHolidays', () => {
  it('computes Easter-based holidays', () => {
    expect(isoDate(easterSunday(2026))).toBe('2026-04-05')
    const he = publicHolidays(2026, 'HE')
    expect(he.get('2026-04-03')).toBe('Karfreitag')
    expect(he.get('2026-06-04')).toBe('Fronleichnam')
  })

  it('knows Heilige Drei Könige in BW, BY and ST only', () => {
    for (const state of ['BW', 'BY', 'ST'] as const) {
      expect(publicHolidays(2026, state).get('2026-01-06')).toBe('Heilige Drei Könige')
    }
    expect(publicHolidays(2026, 'HE').has('2026-01-06')).toBe(false)
  })

  it('knows Weltkindertag in Thüringen', () => {
    expect(publicHolidays(2026, 'TH').get('2026-09-20')).toBe('Weltkindertag')
  })
})
