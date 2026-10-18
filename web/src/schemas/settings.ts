import { z } from 'zod'
import { BUNDESLAND_CODES } from '../utils/germanPublicHolidays'

export const calendarBundeslandSchema = z.enum(BUNDESLAND_CODES)

export const installationSettingsSchema = z.object({
  title: z.string(),
  subtitle: z.string(),
  legalName: z.string(),
  legalAddress: z.string(),
  email: z.string(),
  website: z.string(),
  phone: z.string(),
  representedBy: z.string(),
  register: z.string(),
  contentResponsible: z.string(),
  mapLatitude: z.number(),
  mapLongitude: z.number(),
  hostName: z.string(),
  hostAddress: z.string(),
  hostPrivacyUrl: z.string(),
  authProviderName: z.string(),
  authProviderSameHost: z.boolean(),
  authorityName: z.string(),
  authorityUrl: z.string(),
  calendarBundesland: calendarBundeslandSchema,
})

export type InstallationSettings = z.infer<typeof installationSettingsSchema>

export const installationSettingsPatchSchema = installationSettingsSchema
  .omit({ contentResponsible: true })
  .extend({
    title: z.string().min(1),
    subtitle: z.string().min(1),
  })

export type InstallationSettingsPatch = z.infer<typeof installationSettingsPatchSchema>
