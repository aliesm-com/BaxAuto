import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { AlertTriangle } from 'lucide-react'

import type { BackupRecord } from '@/api/resources'
import { listBackupRecords } from '@/api/resources'
import type { RestoreRecordDTO } from '@/api/restoresApi'
import { listRestoreRecords } from '@/api/restoresApi'
import { listScheduledJobs, type ScheduledJobDTO } from '@/api/schedulesApi'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function AlertsPage() {
  const [backups, setBackups] = useState<BackupRecord[]>([])
  const [restores, setRestores] = useState<RestoreRecordDTO[]>([])
  const [jobs, setJobs] = useState<ScheduledJobDTO[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoadError(null)
      try {
        const [b, r, j] = await Promise.all([listBackupRecords(), listRestoreRecords(), listScheduledJobs()])
        if (cancelled) return
        setBackups(b)
        setRestores(r)
        setJobs(j)
      } catch (e) {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : 'Failed to load')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const failedBackups = useMemo(() => backups.filter((x) => x.status === 'failed').slice(0, 20), [backups])
  const failedRestores = useMemo(() => restores.filter((x) => x.status === 'failed').slice(0, 20), [restores])
  const failedJobs = useMemo(() => jobs.filter((j) => j.last_status === 'failed').slice(0, 20), [jobs])

  const hasIssues = failedBackups.length > 0 || failedRestores.length > 0 || failedJobs.length > 0

  return (
    <div className="space-y-6 p-6 lg:p-8">
      <div className="flex flex-wrap items-start gap-4">
        <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-amber-500/15 text-amber-700 dark:text-amber-400">
          <AlertTriangle className="size-7" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Alerts</h1>
          <p className="text-sm text-muted-foreground">
            Aggregated failures from backups, restores, and scheduled jobs. No separate alerting backend yet.
          </p>
        </div>
      </div>

      {loadError ? <p className="text-sm text-red-600">{loadError}</p> : null}

      {!hasIssues && !loadError ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">No failures detected in recent records.</CardContent>
        </Card>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Failed backups</CardTitle>
            <CardDescription>
              From your backup history —{' '}
              <Link to="/backups" className="text-primary hover:underline">
                open Backups
              </Link>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {failedBackups.length === 0 ? (
              <p className="text-muted-foreground">None.</p>
            ) : (
              failedBackups.map((b) => (
                <div key={b.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-2 last:border-0">
                  <span className="font-medium">
                    #{b.id} {b.connection_name}
                  </span>
                  <Badge variant="destructive">{b.engine}</Badge>
                  <p className="w-full text-xs text-muted-foreground">{b.error_message || 'No message'}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Failed restores</CardTitle>
            <CardDescription>
              <Link to="/logs" className="text-primary hover:underline">
                Activity Logs
              </Link>{' '}
              has full detail.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {failedRestores.length === 0 ? (
              <p className="text-muted-foreground">None.</p>
            ) : (
              failedRestores.map((r) => (
                <div key={r.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-2 last:border-0">
                  <span className="font-mono text-xs">restore #{r.id}</span>
                  <span className="text-muted-foreground">backup {r.backup}</span>
                  <p className="w-full text-xs text-muted-foreground">{r.error_message || 'No message'}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Scheduler jobs (last run failed)</CardTitle>
            <CardDescription>
              <Link to="/schedules" className="text-primary hover:underline">
                Schedules
              </Link>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {failedJobs.length === 0 ? (
              <p className="text-muted-foreground">None.</p>
            ) : (
              failedJobs.map((j) => (
                <div key={j.id} className="flex flex-wrap items-start justify-between gap-2 border-b border-border/60 pb-2 last:border-0">
                  <Link to={`/schedules/${j.id}`} className="font-medium text-primary hover:underline">
                    {j.name}
                  </Link>
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {j.task_key}
                  </Badge>
                  <p className="w-full text-xs text-muted-foreground">{j.last_error || 'No error text'}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
