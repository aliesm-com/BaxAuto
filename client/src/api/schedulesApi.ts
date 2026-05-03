import { apiFetch, apiJson } from '@/api/client'

export interface ScheduledJobDTO {
  id: number
  name: string
  enabled: boolean
  schedule_kind: 'interval' | 'crontab'
  interval_seconds: number | null
  crontab_expression: string
  task_key: string
  payload: Record<string, unknown>
  run_as: number | null
  last_run: string | null
  next_run: string | null
  last_status: string
  last_error: string
  created_at?: string
  updated_at?: string
}

export interface ScheduledJobWritePayload {
  name: string
  enabled?: boolean
  schedule_kind: 'interval' | 'crontab'
  interval_seconds?: number | null
  crontab_expression?: string
  task_key: string
  payload?: Record<string, unknown>
  run_as?: number | null
}

export async function listScheduledJobs(): Promise<ScheduledJobDTO[]> {
  return apiJson<ScheduledJobDTO[]>('/api/scheduled-jobs/')
}

export async function createScheduledJob(body: ScheduledJobWritePayload): Promise<ScheduledJobDTO> {
  return apiJson<ScheduledJobDTO>('/api/scheduled-jobs/', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export type ScheduledJobPatchPayload = Partial<ScheduledJobWritePayload>

export async function getScheduledJob(id: number): Promise<ScheduledJobDTO> {
  return apiJson<ScheduledJobDTO>(`/api/scheduled-jobs/${id}/`)
}

export async function updateScheduledJob(id: number, body: ScheduledJobPatchPayload): Promise<ScheduledJobDTO> {
  return apiJson<ScheduledJobDTO>(`/api/scheduled-jobs/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function deleteScheduledJob(id: number): Promise<void> {
  const res = await apiFetch(`/api/scheduled-jobs/${id}/`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await res.text())
}
