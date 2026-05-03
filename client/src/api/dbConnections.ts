import { apiFetch, apiJson } from '@/api/client'

export const ENGINES = [
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'mariadb', label: 'MariaDB' },
  { value: 'mongodb', label: 'MongoDB' },
  { value: 'redis', label: 'Redis' },
  { value: 'rabbitmq', label: 'RabbitMQ' },
  { value: 'clickhouse', label: 'ClickHouse' },
  { value: 'sqlserver', label: 'Microsoft SQL Server' },
] as const

export type EngineValue = (typeof ENGINES)[number]['value']

export type ConnectionAccessRole = 'owner' | 'viewer' | 'editor'

export interface ConnectionShareDTO {
  user: number
  username: string
  role: ConnectionAccessRole | string
}

export interface DatabaseConnectionDTO {
  id: number
  /** Owner user id (required by scheduler backup task validation). */
  user: number
  owner_username: string
  /** Effective role for the current user (API-computed). */
  access_role: ConnectionAccessRole | string
  name: string
  engine: string
  host: string
  port: number | null
  database_name: string
  username: string
  virtual_host: string
  connection_uri: string
  use_tls: boolean
  extra_options: Record<string, unknown>
  created_at?: string
  updated_at?: string
}

export interface ConnectionWritePayload {
  name: string
  engine: string
  host?: string
  port?: number | null
  database_name?: string
  username?: string
  password?: string
  virtual_host?: string
  connection_uri?: string
  use_tls?: boolean
  extra_options?: Record<string, unknown>
}

export async function listConnections(): Promise<DatabaseConnectionDTO[]> {
  return apiJson<DatabaseConnectionDTO[]>('/api/db-connections/')
}

export async function getConnection(id: number): Promise<DatabaseConnectionDTO> {
  return apiJson<DatabaseConnectionDTO>(`/api/db-connections/${id}/`)
}

export async function createConnection(body: ConnectionWritePayload): Promise<DatabaseConnectionDTO> {
  return apiJson<DatabaseConnectionDTO>('/api/db-connections/', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateConnection(
  id: number,
  body: Partial<ConnectionWritePayload>,
): Promise<DatabaseConnectionDTO> {
  return apiJson<DatabaseConnectionDTO>(`/api/db-connections/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function deleteConnection(id: number): Promise<void> {
  const res = await apiFetch(`/api/db-connections/${id}/`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await res.text())
}

export async function listConnectionShares(connectionId: number): Promise<ConnectionShareDTO[]> {
  return apiJson<ConnectionShareDTO[]>(`/api/db-connections/${connectionId}/shares/`)
}

export async function addConnectionShare(
  connectionId: number,
  body: { user: number; role: 'viewer' | 'editor' },
): Promise<ConnectionShareDTO> {
  return apiJson<ConnectionShareDTO>(`/api/db-connections/${connectionId}/shares/`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function removeConnectionShare(connectionId: number, memberUserId: number): Promise<void> {
  const res = await apiFetch(`/api/db-connections/${connectionId}/shares/${memberUserId}/`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await res.text())
}

export async function triggerBackupDownload(connectionId: number): Promise<{ blob: Blob; filename: string }> {
  const res = await apiFetch(`/api/db-connections/${connectionId}/backup/`, { method: 'POST' })
  if (!res.ok) {
    const t = await res.text()
    throw new Error(t || `Backup failed (${res.status})`)
  }
  const cd = res.headers.get('Content-Disposition')
  let filename = `backup-${connectionId}`
  if (cd) {
    const m = /filename="?([^";]+)"?/i.exec(cd)
    if (m) filename = m[1]
  }
  const blob = await res.blob()
  return { blob, filename }
}
