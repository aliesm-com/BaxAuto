import type { AuthUser, LoginAsResponse, LoginResponse } from '@/types/user'

import { apiFetch, apiJson, apiUrl, clearTokens, setTokens } from './client'

export const IMPERSONATOR_STORAGE_KEY = 'baxauto_impersonator'

export interface ImpersonatorInfo {
  id: number
  username: string
}

export function readImpersonator(): ImpersonatorInfo | null {
  const raw = sessionStorage.getItem(IMPERSONATOR_STORAGE_KEY)
  if (!raw) return null
  try {
    const j = JSON.parse(raw) as { id?: unknown; username?: unknown }
    if (typeof j === 'object' && j !== null && typeof j.id === 'number' && typeof j.username === 'string') {
      return { id: j.id, username: j.username }
    }
  } catch {
    /* legacy numeric-only value */
  }
  const legacyId = Number(raw)
  if (Number.isInteger(legacyId) && legacyId > 0) {
    return { id: legacyId, username: `User #${legacyId}` }
  }
  return null
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await fetch(apiUrl('/api/auth/login/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    const text = await res.text()
    let msg = text
    try {
      const j = JSON.parse(text) as { detail?: string }
      if (j.detail) msg = j.detail
    } catch {
      /* ignore */
    }
    throw new Error(msg || 'Login failed')
  }
  const data = (await res.json()) as LoginResponse
  sessionStorage.removeItem(IMPERSONATOR_STORAGE_KEY)
  setTokens(data.access, data.refresh)
  return data
}

export async function loginAs(userId: number): Promise<LoginAsResponse> {
  const res = await apiFetch('/api/auth/login-as/', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId }),
  })
  if (!res.ok) {
    const text = await res.text()
    let msg = text
    try {
      const j = JSON.parse(text) as { detail?: string }
      if (j.detail) msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch {
      /* ignore */
    }
    throw new Error(msg || 'Login as failed')
  }
  const data = (await res.json()) as LoginAsResponse
  sessionStorage.setItem(
    IMPERSONATOR_STORAGE_KEY,
    JSON.stringify({ id: data.impersonator_id, username: data.impersonator_username }),
  )
  setTokens(data.access, data.refresh)
  return data
}

export async function logout(): Promise<void> {
  const refresh = localStorage.getItem('baxauto_refresh')
  if (refresh) {
    await apiFetch('/api/auth/logout/', {
      method: 'POST',
      body: JSON.stringify({ refresh }),
    }).catch(() => {
      /* blacklist best-effort */
    })
  }
  sessionStorage.removeItem(IMPERSONATOR_STORAGE_KEY)
  clearTokens()
}

export async function fetchMe(): Promise<AuthUser> {
  return apiJson<AuthUser>('/api/auth/me/')
}
