import { z } from 'zod'

import { installationSettingsSchema } from '../api/generated/schemas'

export {
  calendarBundeslandSchema,
  installationSettingsSchema,
  type CalendarBundesland,
  type InstallationSettings,
} from '../api/generated/schemas'

/** Request body of PATCH /api/settings (Inhaltlich Verantwortliche are derived). */
export const installationSettingsPatchSchema = installationSettingsSchema
  .omit({ contentResponsible: true })
  .extend({
    title: z.string().min(1),
    subtitle: z.string().min(1),
  })

export type InstallationSettingsPatch = z.infer<typeof installationSettingsPatchSchema>
