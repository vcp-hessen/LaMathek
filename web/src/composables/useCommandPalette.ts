import { ref } from 'vue'

// One palette for the whole app: the sidebar is mounted twice (desktop and
// mobile drawer), so its open state cannot live in the sidebar.
const open = ref(false)

export function useCommandPalette() {
  return { open }
}
