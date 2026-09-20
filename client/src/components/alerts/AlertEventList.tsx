import { Badge } from '@/components/ui/badge'
import { formatDateTime } from '@/lib/datetime'
import type { AlertEventDTO, AlertStatus } from '@/api/alertsApi'

function statusBadge(status: AlertStatus) {
  if (status === 'warning') {
    return (
      <Badge className="border-transparent bg-amber-500/15 font-normal text-amber-800 dark:text-amber-300">
        warning
      </Badge>
    )
  }
  if (status === 'error') {
    return (
      <Badge variant="destructive" className="font-normal">
        error
      </Badge>
    )
  }
  return (
    <Badge variant="success" className="font-normal">
      success
    </Badge>
  )
}

export function AlertEventList({
  alerts,
  emptyText = 'No alerts yet.',
}: {
  alerts: AlertEventDTO[]
  emptyText?: string
}) {
  if (alerts.length === 0) {
    return <p className="py-6 text-center text-sm text-muted-foreground">{emptyText}</p>
  }

  return (
    <div className="space-y-3">
      {alerts.map((alert) => (
        <div key={alert.id} className="rounded-lg border border-border/70 bg-muted/20 px-3 py-2.5">
          <div className="flex flex-wrap items-center gap-2">
            {statusBadge(alert.status)}
            {alert.source ? (
              <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                {alert.source}
              </span>
            ) : null}
            <span className="ml-auto text-[11px] text-muted-foreground">{formatDateTime(alert.created_at)}</span>
          </div>
          <p className="mt-1.5 text-sm leading-snug">{alert.description}</p>
          {alert.error ? <p className="mt-1 text-xs text-muted-foreground">{alert.error}</p> : null}
        </div>
      ))}
    </div>
  )
}
