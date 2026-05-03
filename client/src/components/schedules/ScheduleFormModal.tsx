import { type FormEvent, useEffect, useState } from 'react'

import { listConnections, type DatabaseConnectionDTO } from '@/api/dbConnections'
import { createScheduledJob, getScheduledJob, updateScheduledJob } from '@/api/schedulesApi'
import { useAuth } from '@/auth/AuthContext'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

const TASK_KEYS = [
  { value: 'noop', label: 'No-op (testing)' },
  { value: 'backup_saved_connection', label: 'Backup saved connection' },
] as const

export interface ScheduleFormModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  jobId?: number
  onSaved?: (detail: { id: number; mode: 'create' | 'edit' }) => void
}

export function ScheduleFormModal({ open, onOpenChange, jobId, onSaved }: ScheduleFormModalProps) {
  const { user } = useAuth()
  const isEdit = jobId != null

  const [name, setName] = useState('')
  const [enabled, setEnabled] = useState(true)
  const [scheduleKind, setScheduleKind] = useState<'interval' | 'crontab'>('interval')
  const [intervalSeconds, setIntervalSeconds] = useState('3600')
  const [crontab, setCrontab] = useState('0 */6 * * *')
  const [taskKey, setTaskKey] = useState<string>('backup_saved_connection')
  const [payloadText, setPayloadText] = useState('{}')
  const [selectedConnectionId, setSelectedConnectionId] = useState<number | ''>('')
  const [connections, setConnections] = useState<DatabaseConnectionDTO[]>([])
  const [connectionsLoading, setConnectionsLoading] = useState(false)
  const [connectionsError, setConnectionsError] = useState<string | null>(null)
  const [runAsText, setRunAsText] = useState('')
  const [loadingJob, setLoadingJob] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setError(null)
    setLoadError(null)

    if (!isEdit) {
      setName('')
      setEnabled(true)
      setScheduleKind('interval')
      setIntervalSeconds('3600')
      setCrontab('0 */6 * * *')
      setTaskKey('backup_saved_connection')
      setPayloadText('{}')
      setSelectedConnectionId('')
      setRunAsText('')
      setLoadingJob(false)
      return
    }

    let cancelled = false
    setLoadingJob(true)
    ;(async () => {
      try {
        const j = await getScheduledJob(jobId)
        if (cancelled) return
        setName(j.name)
        setEnabled(j.enabled)
        setScheduleKind(j.schedule_kind)
        setIntervalSeconds(j.interval_seconds != null ? String(j.interval_seconds) : '3600')
        setCrontab(j.crontab_expression?.trim() || '0 */6 * * *')
        setTaskKey(j.task_key)
        const cid = j.payload?.connection_id
        if (j.task_key === 'backup_saved_connection' && typeof cid === 'number' && Number.isInteger(cid)) {
          setSelectedConnectionId(cid)
          setPayloadText('{}')
        } else if (j.task_key === 'noop') {
          setSelectedConnectionId('')
          setPayloadText(JSON.stringify(j.payload ?? {}, null, 2))
        } else {
          setPayloadText(JSON.stringify(j.payload ?? {}, null, 2))
          setSelectedConnectionId('')
        }
        setRunAsText(j.run_as != null ? String(j.run_as) : '')
      } catch (e) {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : 'Failed to load')
      } finally {
        if (!cancelled) setLoadingJob(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open, isEdit, jobId])

  useEffect(() => {
    if (!open || jobId != null) return
    setRunAsText(user?.id ? String(user.id) : '')
  }, [open, jobId, user?.id])

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setConnectionsLoading(true)
    setConnectionsError(null)
    listConnections()
      .then((rows) => {
        if (!cancelled) setConnections(rows)
      })
      .catch((e) => {
        if (!cancelled) setConnectionsError(e instanceof Error ? e.message : 'Failed to load connections')
      })
      .finally(() => {
        if (!cancelled) setConnectionsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open])

  function applyConnectionPick(id: number | '') {
    setSelectedConnectionId(id)
    if (id === '') return
    const row = connections.find((c) => c.id === id)
    if (row?.user != null) setRunAsText(String(row.user))
  }

  useEffect(() => {
    if (!open || taskKey !== 'backup_saved_connection' || selectedConnectionId === '') return
    const row = connections.find((c) => c.id === selectedConnectionId)
    if (row?.user != null) setRunAsText(String(row.user))
  }, [open, taskKey, connections, selectedConnectionId])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    let payload: Record<string, unknown> = {}

    if (taskKey === 'backup_saved_connection') {
      if (selectedConnectionId === '') {
        setError('Choose a database connection to back up.')
        return
      }
      const cid = selectedConnectionId
      payload = { connection_id: cid }
    } else {
      try {
        payload = JSON.parse(payloadText || '{}') as Record<string, unknown>
      } catch {
        setError('Payload must be valid JSON.')
        return
      }
      if (taskKey === 'noop' && Object.keys(payload).length > 0) {
        setError('No-op task requires an empty object {} as payload.')
        return
      }
    }

    const intervalNum = Number(intervalSeconds)
    if (scheduleKind === 'interval' && (!Number.isFinite(intervalNum) || intervalNum < 60)) {
      setError('Interval must be at least 60 seconds.')
      return
    }

    const runAs = Number(runAsText)
    if (taskKey === 'backup_saved_connection') {
      if (!Number.isInteger(runAs) || runAs < 1) {
        setError('Could not resolve connection owner (run-as user). Pick a connection again.')
        return
      }
    }

    const body = {
      name: name.trim(),
      enabled,
      schedule_kind: scheduleKind,
      interval_seconds: scheduleKind === 'interval' ? intervalNum : null,
      crontab_expression: scheduleKind === 'crontab' ? crontab.trim() : '',
      task_key: taskKey,
      payload,
      run_as: taskKey === 'backup_saved_connection' ? runAs : null,
    }

    setSaving(true)
    try {
      if (isEdit && jobId != null) {
        await updateScheduledJob(jobId, body)
        onSaved?.({ id: jobId, mode: 'edit' })
      } else {
        const created = await createScheduledJob(body)
        onSaved?.({ id: created.id, mode: 'create' })
      }
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const orphanSelection =
    selectedConnectionId !== '' && !connections.some((c) => c.id === selectedConnectionId)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[min(90vh,900px)] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit schedule' : 'Create schedule'}</DialogTitle>
          <DialogDescription>
            Maps to a ScheduledJob row executed by <code className="text-xs">scheduler_tick</code> on the server.
          </DialogDescription>
        </DialogHeader>

        {loadingJob ? (
          <p className="text-sm text-muted-foreground">Loading schedule…</p>
        ) : loadError && isEdit ? (
          <p className="text-sm text-red-600">{loadError}</p>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            {error ? <p className="text-sm text-red-600">{error}</p> : null}

            <div className="space-y-2">
              <Label htmlFor="sched-modal-name">Name</Label>
              <Input id="sched-modal-name" value={name} onChange={(e) => setName(e.target.value)} required placeholder="Nightly PG backup" />
            </div>

            <label className="flex cursor-pointer items-center gap-2">
              <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} className="size-4 rounded" />
              <span className="text-sm font-medium">Enabled</span>
            </label>

            <div className="space-y-2">
              <Label>Schedule type</Label>
              <div className="flex gap-4 text-sm">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="sched-modal-sk"
                    checked={scheduleKind === 'interval'}
                    onChange={() => setScheduleKind('interval')}
                  />
                  Interval
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="sched-modal-sk"
                    checked={scheduleKind === 'crontab'}
                    onChange={() => setScheduleKind('crontab')}
                  />
                  Cron (5-field)
                </label>
              </div>
            </div>

            {scheduleKind === 'interval' ? (
              <div className="space-y-2">
                <Label htmlFor="sched-modal-interval">Interval (seconds)</Label>
                <Input
                  id="sched-modal-interval"
                  inputMode="numeric"
                  value={intervalSeconds}
                  onChange={(e) => setIntervalSeconds(e.target.value)}
                  required
                  min={60}
                />
              </div>
            ) : (
              <div className="space-y-2">
                <Label htmlFor="sched-modal-cron">Cron expression</Label>
                <Input id="sched-modal-cron" value={crontab} onChange={(e) => setCrontab(e.target.value)} required placeholder="15 */6 * * *" />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="sched-modal-task">Task</Label>
              <select
                id="sched-modal-task"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={taskKey}
                onChange={(e) => {
                  const v = e.target.value
                  setTaskKey(v)
                  if (v === 'noop') {
                    setPayloadText('{}')
                    setSelectedConnectionId('')
                  }
                }}
              >
                {TASK_KEYS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            {taskKey === 'backup_saved_connection' ? (
              <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-4">
                <div className="space-y-2">
                  <Label htmlFor="sched-modal-connection">Database connection</Label>
                  <select
                    id="sched-modal-connection"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    disabled={connectionsLoading}
                    value={selectedConnectionId === '' ? '' : String(selectedConnectionId)}
                    onChange={(e) => {
                      const raw = e.target.value
                      applyConnectionPick(raw === '' ? '' : Number(raw))
                    }}
                  >
                    <option value="">Select connection…</option>
                    {connections.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.engine}) · #{c.id}
                      </option>
                    ))}
                    {orphanSelection ? (
                      <option value={selectedConnectionId}>Connection #{selectedConnectionId} (not in your list)</option>
                    ) : null}
                  </select>
                  {connectionsError ? <p className="text-xs text-red-600">{connectionsError}</p> : null}
                  {connectionsLoading ? <p className="text-xs text-muted-foreground">Loading connections…</p> : null}
                  {!connectionsLoading && connections.length === 0 && !connectionsError ? (
                    <p className="text-xs text-muted-foreground">No connections returned for your account. Add one under Databases.</p>
                  ) : null}
                </div>
                <div className="space-y-1">
                  <Label>Run as (connection owner)</Label>
                  <p className="font-mono text-sm text-foreground">{runAsText || '—'}</p>
                  <p className="text-xs text-muted-foreground">
                    The API only lists connections you can access; run-as is set from the connection owner so validation passes on the
                    server.
                  </p>
                </div>
                {orphanSelection ? (
                  <p className="text-xs text-amber-700 dark:text-amber-400">
                    This job targets a connection you cannot see in the list (another user&apos;s resource). Editing may fail unless you use an
                    account that owns it.
                  </p>
                ) : null}
              </div>
            ) : (
              <div className="space-y-2">
                <Label htmlFor="sched-modal-payload">Payload (JSON)</Label>
                <Textarea id="sched-modal-payload" rows={6} className="font-mono text-xs" value={payloadText} onChange={(e) => setPayloadText(e.target.value)} />
                <p className="text-xs text-muted-foreground">Use {'{}'} for noop.</p>
              </div>
            )}

            <DialogFooter className="gap-2 border-t border-border pt-4 sm:justify-between">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Create schedule'}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
