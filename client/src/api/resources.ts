import { apiFetch, apiJson } from './client'

export type { DatabaseConnectionDTO as DbConnection } from './dbConnections'
export { listConnections } from './dbConnections'

export interface BackupStorageUpload {
  id: number
  name: string
  kind: string
  ok: boolean
  remote?: string
  error?: string
}

export interface BackupRecord {
  id: number
  connection: number
  connection_name: string
  trigger: string
  scheduled_job: number | null
  status: string
  engine: string
  relative_media_path: string
  download_filename: string
  size_bytes: number | null
  compressed: boolean
  storage_uploads: BackupStorageUpload[]
  error_message: string
  created_at: string
  finished_at: string | null
}

export async function listBackupRecords() {
  return apiJson<BackupRecord[]>('/api/backup-records/')
}

export async function cancelInProgressBackup(id: number): Promise<void> {
  const res = await apiFetch(`/api/backup-records/${id}/cancel/`, {
    method: 'POST',
    body: '{}',
  })
  if (!res.ok) {
    let detail = `Cancel failed (${res.status})`
    try {
      const body = (await res.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
}
