import { z } from 'zod'

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
})

export type InstallationSettings = z.infer<typeof installationSettingsSchema>

export const installationSettingsPatchSchema = installationSettingsSchema
  .omit({ contentResponsible: true })
  .extend({
    title: z.string().min(1),
    subtitle: z.string().min(1),
  })

export type InstallationSettingsPatch = z.infer<typeof installationSettingsPatchSchema>
