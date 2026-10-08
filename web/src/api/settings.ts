import { api } from './client'
import {
  installationSettingsPatchSchema,
  installationSettingsSchema,
  type InstallationSettings,
} from '../schemas/settings'

export async function fetchInstallationSettings(): Promise<InstallationSettings> {
  const response = await api.get('/api/settings')
  return installationSettingsSchema.parse(response.data)
}

export async function updateInstallationSettings(
  patch: { title: string; subtitle: string },
): Promise<InstallationSettings> {
  const body = installationSettingsPatchSchema.parse(patch)
  const response = await api.patch('/api/settings', body)
  return installationSettingsSchema.parse(response.data)
}
