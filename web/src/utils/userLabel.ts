export function userLabel(user: {
  name?: string | null
  email?: string | null
}): string {
  return user.name ?? user.email ?? '—'
}
