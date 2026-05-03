import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'

import {
  deleteScheduledJob,
  getScheduledJob,
  updateScheduledJob,
  type ScheduledJobDTO,
} from '@/api/schedulesApi'
import { useAuth } from '@/auth/AuthContext'
import { canManageSchedules } from '@/auth/access'
import { ScheduleFormModal } from '@/components/schedules/ScheduleFormModal'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

function scheduleSummary(j: ScheduledJobDTO): string {
  if (j.schedule_kind === 'interval') {
    return j.interval_seconds != null ? `Every ${j.interval_seconds}s` : '—'
  }
  return j.crontab_expression?.trim() || '—'
}

export function ScheduleDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const isAdmin = canManageSchedules(user)

  const [row, setRow] = useState<ScheduledJobDTO | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [editOpen, setEditOpen] = useState(false)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    ;(async () => {
      try {
        const data = await getScheduledJob(Number(id))
        if (!cancelled) setRow(data)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Not found')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id])

  async function onToggleEnabled() {
    if (!row) return
    setBusy(true)
    setError(null)
    try {
      const next = await updateScheduledJob(row.id, { enabled: !row.enabled })
      setRow(next)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Update failed')
    } finally {
      setBusy(false)
    }
  }

  async function onDelete() {
    if (!id || !window.confirm('Delete this scheduled job?')) return
    setBusy(true)
    try {
      await deleteScheduledJob(Number(id))
      navigate('/schedules', { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setBusy(false)
    }
  }

  if (error && !row) {
    return (
      <div className="space-y-4 p-6 lg:p-8">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/schedules">
            <ArrowLeft className="mr-2 size-4" />
            Back
          </Link>
        </Button>
        <p className="text-red-600">{error}</p>
      </div>
    )
  }

  if (!row) {
    return (
      <div className="p-6 lg:p-8">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    )
  }

  const payloadPretty = JSON.stringify(row.payload ?? {}, null, 2)

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6 lg:p-8">
      <ScheduleFormModal
        open={isAdmin && editOpen}
        onOpenChange={setEditOpen}
        jobId={row.id}
        onSaved={async () => {
          try {
            const data = await getScheduledJob(Number(id))
            setRow(data)
          } catch {
            /* ignore */
          }
        }}
      />
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/schedules">
              <ArrowLeft className="size-5" />
            </Link>
          </Button>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">{row.name}</h1>
              <Badge variant={row.enabled ? 'success' : 'muted'}>{row.enabled ? 'Enabled' : 'Disabled'}</Badge>
              <Badge variant="secondary" className="font-mono text-xs">
                {row.task_key}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{scheduleSummary(row)}</p>
          </div>
        </div>
        {isAdmin ? (
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" disabled={busy} onClick={() => void onToggleEnabled()}>
              {row.enabled ? 'Disable' : 'Enable'}
            </Button>
            <Button variant="outline" size="sm" type="button" onClick={() => setEditOpen(true)}>
              <Pencil className="mr-2 size-4" />
              Edit
            </Button>
            <Button variant="destructive" size="sm" disabled={busy} onClick={() => void onDelete()}>
              <Trash2 className="mr-2 size-4" />
              Delete
            </Button>
          </div>
        ) : (
          <p className="max-w-sm text-sm text-muted-foreground">You can view this schedule; only app admins can change or delete it.</p>
        )}
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle>Schedule</CardTitle>
          <CardDescription>Uses <code className="text-xs">manage.py scheduler_tick</code> on the server.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-muted-foreground">Kind</dt>
              <dd className="font-medium capitalize">{row.schedule_kind}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Run as user ID</dt>
              <dd className="font-mono">{row.run_as ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Next run</dt>
              <dd>{row.next_run ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Last run</dt>
              <dd>{row.last_run ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Last status</dt>
              <dd>
                <Badge variant={row.last_status === 'success' ? 'success' : row.last_status === 'failed' ? 'destructive' : 'muted'}>
                  {row.last_status || '—'}
                </Badge>
              </dd>
            </div>
          </dl>
          {row.last_error ? (
            <>
              <Separator />
              <div>
                <p className="mb-1 text-muted-foreground">Last error</p>
                <pre className="max-h-40 overflow-auto rounded-md border border-border bg-muted/40 p-3 font-mono text-xs whitespace-pre-wrap">
                  {row.last_error}
                </pre>
              </div>
            </>
          ) : null}
          <Separator />
          <div>
            <p className="mb-2 text-muted-foreground">Payload</p>
            <pre className="max-h-56 overflow-auto rounded-md border border-border bg-muted/40 p-3 font-mono text-xs">{payloadPretty}</pre>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
