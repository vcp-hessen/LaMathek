/**
 * Workflow colors from the VCP corporate design.
 * Full color for the current step and the main action; the official reduced tone for past steps and outline actions.
 */
export type WorkflowTone = 'blau' | 'wasserblau' | 'erdbraun' | 'feuergelb' | 'feuerrot' | 'luftgrau'

export const managerStepTones: WorkflowTone[] = [
  'blau',
  'wasserblau',
  'erdbraun',
  'feuergelb',
  'luftgrau',
]
export const borrowerStepTones: WorkflowTone[] = [
  'luftgrau',
  'blau',
  'erdbraun',
  'feuergelb',
  'luftgrau',
]

const badge: Record<WorkflowTone, { current: string; past: string; future: string }> = {
  blau: {
    current: 'border-vcp-blau bg-vcp-blau text-white',
    past: 'border-transparent bg-vcp-blau-reduced text-vcp-blau',
    future: 'border-vcp-blau bg-transparent text-vcp-blau',
  },
  wasserblau: {
    current: 'border-vcp-wasserblau bg-vcp-wasserblau text-white',
    past: 'border-transparent bg-vcp-wasserblau-reduced text-vcp-wasserblau',
    future: 'border-vcp-wasserblau bg-transparent text-vcp-wasserblau',
  },
  erdbraun: {
    current: 'border-vcp-erdbraun bg-vcp-erdbraun text-white',
    past: 'border-transparent bg-vcp-erdbraun-reduced text-vcp-erdbraun',
    future: 'border-vcp-erdbraun bg-transparent text-vcp-erdbraun',
  },
  feuergelb: {
    current: 'border-vcp-feuergelb bg-vcp-feuergelb text-vcp-erdbraun',
    past: 'border-transparent bg-vcp-feuergelb-reduced text-vcp-erdbraun',
    future: 'border-vcp-feuergelb bg-transparent text-vcp-erdbraun',
  },
  feuerrot: {
    current: 'border-vcp-feuerrot bg-vcp-feuerrot text-white',
    past: 'border-transparent bg-vcp-feuerrot-reduced text-vcp-feuerrot',
    future: 'border-vcp-feuerrot bg-transparent text-vcp-feuerrot',
  },
  luftgrau: {
    current: 'border-vcp-luftgrau bg-vcp-luftgrau text-vcp-blau',
    past: 'border-transparent bg-vcp-luftgrau text-vcp-blau/70',
    future: 'border-vcp-blau-reduced bg-transparent text-vcp-blau/70',
  },
}

const button: Record<Exclude<WorkflowTone, 'luftgrau'>, { solid: string; outline: string }> = {
  blau: {
    solid: 'border-vcp-blau bg-vcp-blau text-white hover:bg-vcp-blau/90',
    outline:
      'border-vcp-blau bg-transparent text-vcp-blau hover:border-vcp-blau hover:bg-vcp-blau-reduced',
  },
  wasserblau: {
    solid: 'border-vcp-wasserblau bg-vcp-wasserblau text-white hover:bg-vcp-wasserblau/90',
    outline:
      'border-vcp-wasserblau bg-transparent text-vcp-wasserblau hover:border-vcp-wasserblau hover:bg-vcp-wasserblau-reduced',
  },
  erdbraun: {
    solid: 'border-vcp-erdbraun bg-vcp-erdbraun text-white hover:bg-vcp-erdbraun/90',
    outline:
      'border-vcp-erdbraun bg-transparent text-vcp-erdbraun hover:border-vcp-erdbraun hover:bg-vcp-erdbraun-reduced',
  },
  feuergelb: {
    solid: 'border-vcp-feuergelb bg-vcp-feuergelb text-vcp-erdbraun hover:bg-vcp-feuergelb/90',
    outline:
      'border-vcp-feuergelb bg-transparent text-vcp-erdbraun hover:border-vcp-feuergelb hover:bg-vcp-feuergelb-reduced',
  },
  feuerrot: {
    solid: 'border-vcp-feuerrot bg-vcp-feuerrot text-white hover:bg-vcp-feuerrot/90',
    outline:
      'border-vcp-feuerrot bg-transparent text-vcp-feuerrot hover:border-vcp-feuerrot hover:bg-vcp-feuerrot-reduced',
  },
}

export function stepBadgeClass(tone: WorkflowTone, state: 'current' | 'past' | 'future'): string {
  return badge[tone][state]
}

export function stageButtonClass(tone: Exclude<WorkflowTone, 'luftgrau'>, solid = false): string {
  const colors = solid ? button[tone].solid : button[tone].outline
  return `btn btn-sm border ${colors}`
}
