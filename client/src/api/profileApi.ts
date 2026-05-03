import { apiJson } from '@/api/client'

import type { AuthUser } from '@/types/user'

export interface ProfilePatchPayload {
  email?: string
  first_name?: string
  last_name?: string
  phone_number?: string | null
  country_code?: string | null
}

export async function patchProfile(body: ProfilePatchPayload): Promise<AuthUser> {
  return apiJson<AuthUser>('/api/auth/me/', {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function changePassword(old_password: string, new_password: string): Promise<void> {
  await apiJson<unknown>('/api/auth/me/change-password/', {
    method: 'POST',
    body: JSON.stringify({ old_password, new_password }),
  })
}
