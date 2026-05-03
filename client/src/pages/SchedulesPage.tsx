import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { Eye, Pencil, Plus, Trash2 } from 'lucide-react'

import { deleteScheduledJob, listScheduledJobs, type ScheduledJobDTO } from '@/api/schedulesApi'
import { useAuth } from '@/auth/AuthContext'
import { canManageSchedules } from '@/auth/access'
import { ScheduleFormModal } from '@/components/schedules/ScheduleFormModal'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function SchedulesPage() {
  const { user } = useAuth()
  const isAdmin = canManageSchedules(user)

  const [rows, setRows] = useState<ScheduledJobDTO[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()

  const { modalOpen, jobId } = useMemo(() => {
    const showNew = searchParams.get('new') === '1'
    const raw = searchParams.get('edit')
    const parsed = raw ? Number(raw) : NaN
    const editId = Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
    return {
      modalOpen: showNew || editId != null,
      jobId: editId,
    }
  }, [searchParams])

  const closeModal = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.delete('new')
      next.delete('edit')
      return next
    })
  }, [setSearchParams])

  const openCreateModal = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('new', '1')
      next.delete('edit')
      return next
    })
  }, [setSearchParams])

  const openEditModal = useCallback(
    (id: number) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        next.delete('new')
        next.set('edit', String(id))
        return next
      })
    },
    [setSearchParams],
  )

  const refresh = useCallback(() => {
    listScheduledJobs()
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function onDelete(row: ScheduledJobDTO) {
    if (!window.confirm(`Delete schedule “${row.name}”?`)) return
    setBusyId(row.id)
    setError(null)
    try {
      await deleteScheduledJob(row.id)
      refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="space-y-6 p-6 lg:p-8">
      <ScheduleFormModal
        open={isAdmin && modalOpen}
        onOpenChange={(open) => {
          if (!open) closeModal()
        }}
        jobId={jobId}
        onSaved={() => refresh()}
      />

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Schedules</h1>
          <p className="text-sm text-muted-foreground">
            Cron-style or interval triggers backed by Django tasks.
            {!isAdmin ? ' Only app admins can create or edit schedules.' : null}
          </p>
        </div>
        {isAdmin ? (
          <Button type="button" className="rounded-full shadow-md" onClick={openCreateModal}>
            <Plus className="size-4" />
            Create schedule
          </Button>
        ) : null}
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle>Scheduled jobs</CardTitle>
          <CardDescription>
            Run <code className="text-xs">scheduler_tick</code> on the server to execute due jobs. Use actions for detail, edit, or delete.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-3 pr-4 font-medium">Name</th>
                <th className="pb-3 pr-4 font-medium">Schedule</th>
                <th className="pb-3 pr-4 font-medium">Task</th>
                <th className="pb-3 pr-4 font-medium">Enabled</th>
                <th className="pb-3 pr-4 font-medium">Next run</th>
                <th className="pb-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((j) => (
                <tr key={j.id} className="border-b border-border/60 last:border-0">
                  <td className="py-3 pr-4 font-medium">
                    <Link to={`/schedules/${j.id}`} className="text-primary hover:underline">
                      {j.name}
                    </Link>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">
                    {j.schedule_kind === 'interval' ? `Every ${j.interval_seconds}s` : j.crontab_expression || '—'}
                  </td>
                  <td className="py-3 pr-4 font-mono text-xs">{j.task_key}</td>
                  <td className="py-3 pr-4">
                    <Badge variant={j.enabled ? 'success' : 'muted'}>{j.enabled ? 'Yes' : 'No'}</Badge>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">{j.next_run ?? '—'}</td>
                  <td className="py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" className="size-8" asChild>
                        <Link to={`/schedules/${j.id}`}>
                          <Eye className="size-4" />
                          <span className="sr-only">View</span>
                        </Link>
                      </Button>
                      {isAdmin ? (
                        <Button type="button" variant="ghost" size="icon" className="size-8" onClick={() => openEditModal(j.id)}>
                          <Pencil className="size-4" />
                          <span className="sr-only">Edit</span>
                        </Button>
                      ) : null}
                      {isAdmin ? (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="size-8 text-destructive hover:text-destructive"
                          disabled={busyId === j.id}
                          onClick={() => void onDelete(j)}
                        >
                          <Trash2 className="size-4" />
                          <span className="sr-only">Delete</span>
                        </Button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && !error ? (
            <p className="py-8 text-center text-muted-foreground">
              No schedules yet.
              {isAdmin ? (
                <>
                  {' '}
                  <button type="button" className="font-medium text-primary underline-offset-4 hover:underline" onClick={openCreateModal}>
                    Create one
                  </button>
                  .
                </>
              ) : null}
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
