import type { Ref } from 'vue'

/**
 * Copy server values into form fields without wiping unsaved edits: a field is
 * only updated if it still holds the value last copied from the server.
 */
export function useServerSyncedFields<K extends string>(fields: Record<K, Ref<string>>) {
  let synced: Partial<Record<K, string>> | null = null

  return function sync(values: Record<K, string>, { force = false } = {}) {
    for (const key of Object.keys(fields) as K[]) {
      const field = fields[key]
      const untouched = synced === null || field.value === synced[key]
      if (force || untouched) field.value = values[key]
    }
    synced = { ...values }
  }
}
