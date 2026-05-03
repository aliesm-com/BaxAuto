import { apiJson } from '@/api/client'

export interface OverviewActivityDay {
  date: string
  weekday: string
  success_count: number
}

export interface OverviewBackupShort {
  id: number
  connection: number
  connection_name: string
  engine: string
  created_at: string
  finished_at: string | null
  size_bytes: number | null
}

export interface OverviewSchedulerHealth {
  visible: boolean
  enabled_jobs: number
  failed_jobs: number
  status: 'ok' | 'issues' | 'unknown'
}

export interface OverviewDTO {
  generated_at: string
  connections: { count: number }
  backups: {
    total: number
    success: number
    failed: number
    in_progress: number
  }
  storage: {
    used_bytes: number
    quota_bytes: number
    quota_percent: number
  }
  last_success: OverviewBackupShort | null
  recent_success: OverviewBackupShort[]
  activity_week: OverviewActivityDay[]
  trend_percent: number | null
  trend_new: boolean
  sparkline: number[]
  health: {
    scheduler: OverviewSchedulerHealth
    workers_configured: number | null
  }
}

export async function fetchOverview(): Promise<OverviewDTO> {
  return apiJson<OverviewDTO>('/api/overview/')
}
