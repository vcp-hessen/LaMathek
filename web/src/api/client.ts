import axios from 'axios'

export const api = axios.create({
  withCredentials: true,
  headers: {
    Accept: 'application/json',
    // Required by the API on every state-changing request (CSRF guard): a
    // cross-site form cannot set custom headers.
    'X-Requested-With': 'lamathek',
  },
})

/**
 * Retry a failed query only when trying again can help: no answer at all or a
 * server error. A 4xx (gone, forbidden, signed out) is shown at once.
 */
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (failureCount >= 2) return false
  const status = axios.isAxiosError(error) ? error.response?.status : undefined
  return status === undefined || status >= 500
}

type UnauthorizedHandler = () => void
let onUnauthorized: UnauthorizedHandler | null = null

/** Called once the session has expired (any 401 except the "who am I" probe). */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  onUnauthorized = handler
}

api.interceptors.response.use(undefined, (error) => {
  const status = error?.response?.status
  const url: string = error?.config?.url ?? ''
  if (status === 401 && !url.endsWith('/api/me') && onUnauthorized) onUnauthorized()
  return Promise.reject(error)
})
