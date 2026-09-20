import { apiJson } from './client'

export type AlertStatus = 'success' | 'warning' | 'error'
export type AlertWebhookStatus = 'up' | 'degraded' | 'down'

export interface AlertEventDTO {
  id: number
  status: AlertStatus
  webhook_status: AlertWebhookStatus
  source: string
  error: string
  description: string
  created_at: string
}

export async function listAlerts(source?: string): Promise<AlertEventDTO[]> {
  const qs = source ? `?source=${encodeURIComponent(source)}` : ''
  return apiJson<AlertEventDTO[]>(`/api/alerts/${qs}`)
}
