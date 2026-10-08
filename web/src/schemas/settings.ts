import { z } from 'zod'

export const installationSettingsSchema = z.object({
  title: z.string(),
  subtitle: z.string(),
})

export type InstallationSettings = z.infer<typeof installationSettingsSchema>

export const installationSettingsPatchSchema = z.object({
  title: z.string().min(1),
  subtitle: z.string().min(1),
})
