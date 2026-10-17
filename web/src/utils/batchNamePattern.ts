export const BATCH_NAME_PLACEHOLDER_TOKENS = {
  number: '{n}',
  letter: '{a}',
  letterUpper: '{A}',
  roman: '{r}',
  romanUpper: '{R}',
} as const

export type BatchNamePlaceholderKind = keyof typeof BATCH_NAME_PLACEHOLDER_TOKENS

export function batchPlaceholderToken(kind: BatchNamePlaceholderKind): string {
  return BATCH_NAME_PLACEHOLDER_TOKENS[kind]
}

export function activeBatchPlaceholder(pattern: string): string | null {
  const tokens = Object.values(BATCH_NAME_PLACEHOLDER_TOKENS)
  const found = tokens.filter((token) => pattern.includes(token))
  if (found.length !== 1) return null
  return found[0]
}

export function batchPlaceholderKindFromPattern(pattern: string): BatchNamePlaceholderKind | null {
  const token = activeBatchPlaceholder(pattern)
  if (!token) return null
  const entry = Object.entries(BATCH_NAME_PLACEHOLDER_TOKENS).find(([, value]) => value === token)
  return (entry?.[0] as BatchNamePlaceholderKind) ?? null
}

function letterAt(index: number, upper: boolean): string {
  if (index < 1 || index > 26) return ''
  const base = upper ? 65 : 96
  return String.fromCharCode(base + index - 1)
}

function romanAt(num: number, upper: boolean): string {
  if (num < 1 || num > 3999) return ''
  const values = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
  const symbols = ['m', 'cm', 'd', 'cd', 'c', 'xc', 'l', 'xl', 'x', 'ix', 'v', 'iv', 'i']
  let n = num
  let result = ''
  for (let i = 0; i < values.length; i += 1) {
    while (n >= values[i]) {
      result += symbols[i]
      n -= values[i]
    }
  }
  return upper ? result.toUpperCase() : result
}

function valueForPlaceholder(token: string, index: number): string {
  if (token === BATCH_NAME_PLACEHOLDER_TOKENS.number) return String(index)
  if (token === BATCH_NAME_PLACEHOLDER_TOKENS.letter) return letterAt(index, false)
  if (token === BATCH_NAME_PLACEHOLDER_TOKENS.letterUpper) return letterAt(index, true)
  if (token === BATCH_NAME_PLACEHOLDER_TOKENS.roman) return romanAt(index, false)
  if (token === BATCH_NAME_PLACEHOLDER_TOKENS.romanUpper) return romanAt(index, true)
  return ''
}

export function pieceNamesFromPattern(pattern: string, count: number): string[] {
  const normalized = pattern.trim()
  const token = activeBatchPlaceholder(normalized)
  if (!token || normalized.split(token).length - 1 !== 1) return []
  const total = Math.min(Math.max(1, Math.floor(count) || 1), 24)
  return Array.from({ length: total }, (_, offset) => {
    const index = offset + 1
    const replacement = valueForPlaceholder(token, index)
    if (!replacement) return ''
    return normalized.replace(token, replacement)
  }).filter(Boolean)
}

export function stripBatchPlaceholders(pattern: string): string {
  let result = pattern
  for (const token of Object.values(BATCH_NAME_PLACEHOLDER_TOKENS)) {
    result = result.replaceAll(token, '')
  }
  return result
}
