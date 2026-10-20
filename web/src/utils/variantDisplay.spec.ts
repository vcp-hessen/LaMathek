import { describe, expect, it } from 'vitest'

import { stockName, variantKey } from './variantDisplay'

describe('variantKey', () => {
  it('matches the server key: sorted, compact, empty values dropped', () => {
    expect(variantKey({ Länge: '3 m', Farbe: 'rot' })).toBe('{"Farbe":"rot","Länge":"3 m"}')
    expect(variantKey({ Länge: '' })).toBe('{}')
    expect(variantKey(undefined)).toBe('{}')
  })
})

describe('stockName', () => {
  it('appends the combination in brackets', () => {
    expect(stockName('Seil', { Länge: '3 m' })).toBe('Seil (3 m)')
    expect(stockName('Hering', {})).toBe('Hering')
  })
})
