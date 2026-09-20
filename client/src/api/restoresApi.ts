import { apiFetch, apiJson } from '@/api/client'

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
  /** Download from this storage destination before restore; omit for local MEDIA. */
  storage_id?: number | null
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

export async function cancelInProgressRestore(id: number): Promise<void> {
  const res = await apiFetch(`/api/restore-records/${id}/cancel/`, {
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
