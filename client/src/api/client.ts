const ACCESS = 'baxauto_access'
const REFRESH = 'baxauto_refresh'

export function apiUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`
  const base = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')
  return base ? `${base}${p}` : p
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH)
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS, access)
  localStorage.setItem(REFRESH, refresh)
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS)
  localStorage.removeItem(REFRESH)
}

async function tryRefresh(): Promise<string | null> {
  const refresh = getRefreshToken()
  if (!refresh) return null
  const res = await fetch(apiUrl('/api/auth/refresh/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
  if (!res.ok) {
    clearTokens()
    return null
  }
  const data = (await res.json()) as { access: string }
  localStorage.setItem(ACCESS, data.access)
  return data.access
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  const token = getAccessToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (!headers.has('Content-Type') && init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  let res = await fetch(apiUrl(path), { ...init, headers })

  if (res.status === 401 && getRefreshToken()) {
    const next = await tryRefresh()
    if (next) {
      headers.set('Authorization', `Bearer ${next}`)
      res = await fetch(apiUrl(path), { ...init, headers })
    }
  }

  return res
}

export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, init)
  if (!res.ok) {
    const text = await res.text()
    let detail = text
    try {
      const j = JSON.parse(text) as { detail?: unknown }
      if (typeof j.detail === 'string') detail = j.detail
      else if (Array.isArray(j.detail)) detail = JSON.stringify(j.detail)
    } catch {
      /* ignore */
    }
    throw new Error(detail || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}
