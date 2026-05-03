import { apiJson } from '@/api/client'

export interface RestoreRecordDTO {
  id: number
  backup: number
  connection: number
  initiated_by: number | null
  initiated_by_username: string | null
  status: string
  engine: string
  options: Record<string, unknown>
  error_message: string
  created_at: string
  finished_at: string | null
}

export interface RestoreRequestBody {
  flush_before_restore?: boolean
  apply_schema?: boolean
  truncate_first?: boolean
  drop?: boolean
}

export async function listRestoreRecords(): Promise<RestoreRecordDTO[]> {
  return apiJson<RestoreRecordDTO[]>('/api/restore-records/')
}

export async function triggerRestore(backupId: number, body: RestoreRequestBody = {}): Promise<RestoreRecordDTO> {
  return apiJson<RestoreRecordDTO>(`/api/backup-records/${backupId}/restore/`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
