import { useQuery } from '@tanstack/vue-query'

import { fetchMe } from '../api/me'
import { queryKeys } from '../api/queryKeys'

/** The signed-in user (or the impersonated one), shared by every component. */
export function useMe() {
  return useQuery({ queryKey: queryKeys.me, queryFn: fetchMe })
}
