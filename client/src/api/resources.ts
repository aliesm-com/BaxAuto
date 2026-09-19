import { apiJson } from './client'

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
