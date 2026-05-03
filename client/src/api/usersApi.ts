import { apiFetch, apiJson } from '@/api/client'

import type { AuthUser } from '@/types/user'

/** Admin list/detail includes Django flags read-only (not editable via API). */
export interface AdminUserDTO extends AuthUser {
  is_staff: boolean
}

export interface AdminUserWritePayload {
  username: string
  email?: string
  first_name?: string
  last_name?: string
  is_active?: boolean
  is_viewer?: boolean
  is_editor?: boolean
  is_admin?: boolean
  phone_number?: string | null
  country_code?: string | null
  password?: string
}

export async function listUsers(): Promise<AdminUserDTO[]> {
  return apiJson<AdminUserDTO[]>('/api/auth/users/')
}

export async function getUser(id: number): Promise<AdminUserDTO> {
  return apiJson<AdminUserDTO>(`/api/auth/users/${id}/`)
}

export async function createUser(body: AdminUserWritePayload): Promise<AdminUserDTO> {
  return apiJson<AdminUserDTO>('/api/auth/users/', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateUser(id: number, body: Partial<AdminUserWritePayload>): Promise<AdminUserDTO> {
  return apiJson<AdminUserDTO>(`/api/auth/users/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function deleteUser(id: number): Promise<void> {
  const res = await apiFetch(`/api/auth/users/${id}/`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await res.text())
}
