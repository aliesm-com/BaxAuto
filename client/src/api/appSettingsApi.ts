import { apiJson } from '@/api/client'

export interface AppSettingsDTO {
  keep_local_backups: boolean
  updated_at: string
}

export async function getAppSettings(): Promise<AppSettingsDTO> {
  return apiJson<AppSettingsDTO>('/api/app-settings/')
}

export async function patchAppSettings(body: { keep_local_backups: boolean }): Promise<AppSettingsDTO> {
  return apiJson<AppSettingsDTO>('/api/app-settings/', {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}
