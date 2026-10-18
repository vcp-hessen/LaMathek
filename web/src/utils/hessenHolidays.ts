/** @deprecated Import from germanPublicHolidays instead. */
import { DEFAULT_BUNDESLAND, publicHolidays } from './germanPublicHolidays'

export {
  DEFAULT_BUNDESLAND,
  easterSunday,
  isoDate,
  isWeekend,
  publicHolidays,
} from './germanPublicHolidays'

export function hessenHolidays(year: number): Map<string, string> {
  return publicHolidays(year, DEFAULT_BUNDESLAND)
}
