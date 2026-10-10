import axios from 'axios'

export function apiErrorCode(error: unknown): string | null {
  if (
    axios.isAxiosError(error) &&
    error.response?.data &&
    typeof error.response.data === 'object' &&
    'error' in error.response.data
  ) {
    const code = (error.response.data as { error: unknown }).error
    return typeof code === 'string' ? code : null
  }
  return null
}
