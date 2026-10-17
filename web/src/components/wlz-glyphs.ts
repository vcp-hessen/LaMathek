/** Lexikon-Buchstaben der Schrift waldlaeuferzeichen-pfadfinden (VCP Corporate Design). */
export type WlzGlyphId =
  | 'campPath'
  | 'split'
  | 'full'
  | 'empty'
  | 'gather'
  | 'gatherHere'
  | 'exchange'
  | 'please'
  | 'day'
  | 'night'
  | 'opposite'
  | 'thisWay'
  | 'geheim'
  | 'backToStart'

export const WLZ_GLYPH: Record<WlzGlyphId, string> = {
  campPath: 'z',
  split: 'B',
  full: 'X',
  empty: 'Y',
  gather: 'V',
  gatherHere: 'U',
  exchange: 'v',
  please: 'w',
  day: 't',
  night: 's',
  opposite: 'y',
  thisWay: 'x',
  geheim: 'W',
  backToStart: 'N',
}
