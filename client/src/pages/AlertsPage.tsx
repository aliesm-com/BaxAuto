import { useCallback, useEffect, useState } from 'react'

import { ShieldAlert } from 'lucide-react'

import type { AlertEventDTO } from '@/api/alertsApi'
import { listAlerts } from '@/api/alertsApi'
import { AlertEventList } from '@/components/alerts/AlertEventList'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertEventDTO[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  const refresh = useCallback(() => {
    setLoadError(null)
    listAlerts()
      .then(setAlerts)
      .catch((e) => setLoadError(e instanceof Error ? e.message : 'Failed to load'))
  }, [])

  useEffect(() => {
    refresh()
    const id = window.setInterval(refresh, 30000)
    return () => window.clearInterval(id)
  }, [refresh])

  return (
    <div className="space-y-6 p-6 lg:p-8">
      <div className="flex flex-wrap items-start gap-4">
        <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-amber-500/15 text-amber-700 dark:text-amber-400">
          <ShieldAlert className="size-7" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Alerts</h1>
          <p className="text-sm text-muted-foreground">
            Errors and warnings from backups, restores, schedules, and the API. Matching events are also sent to the
            configured webhook.
          </p>
        </div>
      </div>

      {loadError ? <p className="text-sm text-red-600">{loadError}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent alerts</CardTitle>
          <CardDescription>
            {alerts.length === 0 ? 'Nothing to show yet.' : `${alerts.length} recent event${alerts.length === 1 ? '' : 's'}`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AlertEventList alerts={alerts} emptyText="No alerts yet. Failures will appear here automatically." />
        </CardContent>
      </Card>
    </div>
  )
}
