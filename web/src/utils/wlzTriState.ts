import type { WlzGlyphId } from '../components/wlz-glyphs'

export type WlzTriState = 'off' | 'partial' | 'on'

export function wlzGlyphForTriState(state: WlzTriState): WlzGlyphId {
  switch (state) {
    case 'on':
      return 'full'
    case 'partial':
      return 'split'
    default:
      return 'empty'
  }
}

export function wlzTriStateButtonClass(
  state: WlzTriState,
  size: 'xs' | 'sm' | 'md' = 'xs',
): string {
  const sizeClass = size === 'xs' ? 'btn-xs' : size === 'md' ? 'btn-md' : 'btn-sm'
  const tone =
    state === 'off'
      ? 'btn-ghost text-vcp-blau hover:bg-vcp-blau/10'
      : 'border-transparent bg-vcp-feuergelb text-vcp-erdbraun hover:bg-vcp-feuergelb/80'
  return ['btn gap-1', sizeClass, tone].join(' ')
}

export function cycleTriState(
  current: WlzTriState,
  options: { binary?: boolean; allowPartial?: boolean } = {},
): WlzTriState {
  const { binary = false, allowPartial = true } = options
  if (binary) {
    return current === 'off' ? 'on' : 'off'
  }
  const order: WlzTriState[] = allowPartial
    ? ['off', 'partial', 'on']
    : ['off', 'on']
  const index = order.indexOf(current)
  const nextIndex = index < 0 ? 0 : (index + 1) % order.length
  return order[nextIndex]
}
