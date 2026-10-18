/** Gesetzliche Feiertage nach Bundesland (vereinfachtes bundesweites Regelwerk). */

export const BUNDESLAND_CODES = [
  'BW',
  'BY',
  'BE',
  'BB',
  'HB',
  'HH',
  'HE',
  'MV',
  'NI',
  'NW',
  'RP',
  'SL',
  'SN',
  'ST',
  'SH',
  'TH',
] as const

export type BundeslandCode = (typeof BUNDESLAND_CODES)[number]

export const DEFAULT_BUNDESLAND: BundeslandCode = 'HE'

export const BUNDESLAND_LABELS: Record<BundeslandCode, string> = {
  BW: 'Baden-Württemberg',
  BY: 'Bayern',
  BE: 'Berlin',
  BB: 'Brandenburg',
  HB: 'Bremen',
  HH: 'Hamburg',
  HE: 'Hessen',
  MV: 'Mecklenburg-Vorpommern',
  NI: 'Niedersachsen',
  NW: 'Nordrhein-Westfalen',
  RP: 'Rheinland-Pfalz',
  SL: 'Saarland',
  SN: 'Sachsen',
  ST: 'Sachsen-Anhalt',
  SH: 'Schleswig-Holstein',
  TH: 'Thüringen',
}

export function easterSunday(year: number): Date {
  const a = year % 19
  const b = Math.floor(year / 100)
  const c = year % 100
  const d = Math.floor(b / 4)
  const e = b % 4
  const f = Math.floor((b + 8) / 25)
  const g = Math.floor((b - f + 1) / 3)
  const h = (19 * a + b - d - g + 15) % 30
  const i = Math.floor(c / 4)
  const k = c % 4
  const l = (32 + 2 * e + 2 * i - h - k) % 7
  const m = Math.floor((a + 11 * h + 22 * l) / 451)
  const month = Math.floor((h + l - 7 * m + 114) / 31)
  const day = ((h + l - 7 * m + 114) % 31) + 1
  return new Date(year, month - 1, day)
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

export function isoDate(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** Buß- und Bettag (Sachsen): Mittwoch vor dem 23. November. */
function bussUndBettag(year: number): Date {
  const cursor = new Date(year, 10, 22)
  while (cursor.getDay() !== 3) {
    cursor.setDate(cursor.getDate() - 1)
  }
  return cursor
}

const REFORMATION_STATES: ReadonlySet<BundeslandCode> = new Set([
  'BB',
  'HB',
  'HH',
  'MV',
  'NI',
  'SN',
  'ST',
  'SH',
  'TH',
])

const FRONLEICHNAM_STATES: ReadonlySet<BundeslandCode> = new Set(['BW', 'BY', 'HE', 'NW', 'RP', 'SL'])

const ALLERHEILIGEN_STATES: ReadonlySet<BundeslandCode> = new Set(['BW', 'BY', 'NW', 'RP', 'SL'])

export function publicHolidays(year: number, state: BundeslandCode): Map<string, string> {
  const easter = easterSunday(year)
  const entries: [string, string][] = [
    [`${year}-01-01`, 'Neujahr'],
    [isoDate(addDays(easter, -2)), 'Karfreitag'],
    [isoDate(addDays(easter, 1)), 'Ostermontag'],
    [`${year}-05-01`, 'Tag der Arbeit'],
    [isoDate(addDays(easter, 39)), 'Christi Himmelfahrt'],
    [isoDate(addDays(easter, 50)), 'Pfingstmontag'],
    [`${year}-10-03`, 'Tag der Deutschen Einheit'],
    [`${year}-12-25`, '1. Weihnachtstag'],
    [`${year}-12-26`, '2. Weihnachtstag'],
  ]

  if (state === 'BY') {
    entries.push([`${year}-01-06`, 'Heilige Drei Könige'])
  }
  if (state === 'BE' || state === 'MV') {
    entries.push([`${year}-03-08`, 'Internationaler Frauentag'])
  }
  if (FRONLEICHNAM_STATES.has(state)) {
    entries.push([isoDate(addDays(easter, 60)), 'Fronleichnam'])
  }
  if (ALLERHEILIGEN_STATES.has(state)) {
    entries.push([`${year}-11-01`, 'Allerheiligen'])
  }
  if (state === 'SL') {
    entries.push([`${year}-08-15`, 'Mariä Himmelfahrt'])
  }
  if (REFORMATION_STATES.has(state)) {
    entries.push([`${year}-10-31`, 'Reformationstag'])
  }
  if (state === 'SN') {
    entries.push([isoDate(bussUndBettag(year)), 'Buß- und Bettag'])
  }
  if (state === 'TH') {
    entries.push([`${year}-09-20`, 'Weltkindertag'])
  }

  return new Map(entries)
}

export function isWeekend(date: Date): boolean {
  const day = date.getDay()
  return day === 0 || day === 6
}

export function isBundeslandCode(value: string): value is BundeslandCode {
  return (BUNDESLAND_CODES as readonly string[]).includes(value)
}
