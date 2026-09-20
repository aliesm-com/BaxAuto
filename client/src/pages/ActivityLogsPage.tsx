import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { Database, HardDrive, Square } from 'lucide-react'

import type { BackupRecord } from '@/api/resources'
import { cancelInProgressBackup, listBackupRecords } from '@/api/resources'
import type { RestoreRecordDTO } from '@/api/restoresApi'
import { cancelInProgressRestore, listRestoreRecords } from '@/api/restoresApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDateTime } from '@/lib/datetime'

type LogKind = 'backup' | 'restore'

interface LogRow {
  key: string
  kind: LogKind
  id: number
  engine: string
  status: string
  actor: string
  created_at: string
  note: string
  connectionId: number
}

function asLogRows(backups: BackupRecord[], restores: RestoreRecordDTO[]): LogRow[] {
  const backupRows: LogRow[] = backups.map((b) => ({
    key: `backup-${b.id}`,
    kind: 'backup',
    id: b.id,
    engine: b.engine,
    status: b.status,
    actor: b.trigger,
    created_at: b.created_at,
    note: b.error_message || b.download_filename || '—',
    connectionId: b.connection,
  }))
  const restoreRows: LogRow[] = restores.map((r) => ({
    key: `restore-${r.id}`,
    kind: 'restore',
    id: r.id,
    engine: r.engine,
    status: r.status,
    actor: r.initiated_by_username ?? '—',
    created_at: r.created_at,
    note: r.error_message || '—',
    connectionId: r.connection,
  }))
  return [...backupRows, ...restoreRows].sort((a, b) => b.created_at.localeCompare(a.created_at))
}

export function ActivityLogsPage() {
  const [backups, setBackups] = useState<BackupRecord[]>([])
  const [restores, setRestores] = useState<RestoreRecordDTO[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busyKey, setBusyKey] = useState<string | null>(null)

  const refresh = useCallback(() => {
    Promise.all([listBackupRecords(), listRestoreRecords()])
      .then(([b, r]) => {
        setBackups(b)
        setRestores(r)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const rows = useMemo(() => asLogRows(backups, restores), [backups, restores])

  async function onCancel(r: LogRow) {
    if (
      !window.confirm(
        `Stop and remove this in-progress ${r.kind} #${r.id}? This cannot be undone.`,
      )
    ) {
      return
    }
    setBusyKey(r.key)
    setError(null)
    try {
      if (r.kind === 'backup') {
        await cancelInProgressBackup(r.id)
        setBackups((prev) => prev.filter((b) => b.id !== r.id))
      } else {
        await cancelInProgressRestore(r.id)
        setRestores((prev) => prev.filter((row) => row.id !== r.id))
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Cancel failed')
    } finally {
      setBusyKey(null)
    }
  }

  return (
    <div className="space-y-6 p-6 lg:p-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Activity Logs</h1>
        <p className="text-sm text-muted-foreground">
          Backup and restore attempts for your database connections.
        </p>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle>History</CardTitle>
          <CardDescription>Newest first. In-progress rows can be stopped and removed.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-3 pr-4 font-medium">Type</th>
                <th className="pb-3 pr-4 font-medium">ID</th>
                <th className="pb-3 pr-4 font-medium">Engine</th>
                <th className="pb-3 pr-4 font-medium">Status</th>
                <th className="pb-3 pr-4 font-medium">By / trigger</th>
                <th className="pb-3 pr-4 font-medium">Started</th>
                <th className="pb-3 pr-4 font-medium max-w-[200px]">Note</th>
                <th className="pb-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} className="border-b border-border/60 last:border-0">
                  <td className="py-3 pr-4 capitalize">{r.kind}</td>
                  <td className="py-3 pr-4 font-mono text-xs">#{r.id}</td>
                  <td className="py-3 pr-4 capitalize">{r.engine}</td>
                  <td className="py-3 pr-4">
                    <Badge variant={r.status === 'success' ? 'success' : r.status === 'failed' ? 'destructive' : 'muted'}>
                      {r.status}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">{r.actor}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{formatDateTime(r.created_at)}</td>
                  <td className="max-w-[200px] truncate py-3 pr-4 text-xs text-muted-foreground" title={r.note}>
                    {r.note.length > 80 ? `${r.note.slice(0, 80)}…` : r.note}
                  </td>
                  <td className="py-3 text-right">
                    <div className="flex justify-end gap-1">
                      {r.status === 'in_progress' ? (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-destructive"
                          type="button"
                          disabled={busyKey === r.key}
                          title="Stop and remove"
                          onClick={() => void onCancel(r)}
                        >
                          <Square className="size-4" />
                          <span className="sr-only">Stop</span>
                        </Button>
                      ) : null}
                      {r.kind === 'backup' ? (
                        <Button variant="ghost" size="icon" className="size-8" asChild>
                          <Link to="/backups">
                            <HardDrive className="size-4" />
                            <span className="sr-only">Backups</span>
                          </Link>
                        </Button>
                      ) : null}
                      <Button variant="ghost" size="icon" className="size-8" asChild>
                        <Link to={`/databases/${r.connectionId}`}>
                          <Database className="size-4" />
                          <span className="sr-only">Connection</span>
                        </Link>
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && !error ? (
            <p className="py-8 text-center text-muted-foreground">No backup or restore activity yet.</p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
