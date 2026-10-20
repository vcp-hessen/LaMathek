import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import { useServerSyncedFields } from './useServerSyncedFields'

describe('useServerSyncedFields', () => {
  it('keeps unsaved edits but takes server changes of untouched fields', () => {
    const group = ref('')
    const note = ref('')
    const sync = useServerSyncedFields({ group, note })
    sync({ group: 'Stamm A', note: 'Schlüssel' })
    expect([group.value, note.value]).toEqual(['Stamm A', 'Schlüssel'])

    group.value = 'Stamm B' // typing, not saved yet
    sync({ group: 'Stamm A', note: 'Schlüssel bei Mara' })
    expect([group.value, note.value]).toEqual(['Stamm B', 'Schlüssel bei Mara'])

    sync({ group: 'Stamm C', note: '' }, { force: true }) // another Verleih
    expect([group.value, note.value]).toEqual(['Stamm C', ''])
  })
})
