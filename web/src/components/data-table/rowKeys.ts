/** Rows that act like buttons: Enter or Space runs the row action. */
export function activateOnKey(event: KeyboardEvent, action: () => void): void {
  if (event.key !== 'Enter' && event.key !== ' ') return
  event.preventDefault()
  action()
}
