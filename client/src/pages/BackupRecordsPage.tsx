import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Database, Download, RotateCcw, Square } from 'lucide-react'

import type { BackupRecord } from '@/api/resources'
import { cancelInProgressBackup, listBackupRecords } from '@/api/resources'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { downloadAuthenticated } from '@/lib/download'
import { formatDateTime } from '@/lib/datetime'

export function BackupRecordsPage() {
  const [rows, setRows] = useState<BackupRecord[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  const refresh = useCallback(() => {
    listBackupRecords()
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function onCancel(b: BackupRecord) {
    if (
      !window.confirm(
        `Stop and remove in-progress backup #${b.id} for “${b.connection_name}”? This cannot be undone.`,
      )
    ) {
      return
    }
    setBusyId(b.id)
    setError(null)
    try {
      await cancelInProgressBackup(b.id)
      setRows((prev) => prev.filter((row) => row.id !== b.id))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Cancel failed')
    } finally {
      setBusyId(null)
    }
  }

  const inProgressCount = rows.filter((b) => b.status === 'in_progress').length

  return (
    <div className="space-y-6 p-6 lg:p-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Backups</h1>
        <p className="text-sm text-muted-foreground">
          Logical backups recorded for your connections. Successful files are also copied to every storage destination you have configured.
          {inProgressCount > 0
            ? ` ${inProgressCount} run(s) still in progress — you can stop and remove them below.`
            : ''}
        </p>
      </div>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <Card>
        <CardHeader>
          <CardTitle>Backup records</CardTitle>
          <CardDescription>Includes scheduled and manual runs.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-3 pr-4 font-medium">Connection</th>
                <th className="pb-3 pr-4 font-medium">Engine</th>
                <th className="pb-3 pr-4 font-medium">Trigger</th>
                <th className="pb-3 pr-4 font-medium">Status</th>
                <th className="pb-3 pr-4 font-medium">Storage</th>
                <th className="pb-3 pr-4 font-medium">Finished</th>
                <th className="pb-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((b) => (
                <tr key={b.id} className="border-b border-border/60 last:border-0">
                  <td className="py-3 pr-4 font-medium">{b.connection_name}</td>
                  <td className="py-3 pr-4 capitalize">{b.engine}</td>
                  <td className="py-3 pr-4">{b.trigger}</td>
                  <td className="py-3 pr-4">
                    <div className="flex flex-wrap items-center gap-1">
                      <Badge variant={b.status === 'success' ? 'success' : b.status === 'failed' ? 'destructive' : 'muted'}>
                        {b.status}
                      </Badge>
                      {b.compressed ? (
                        <Badge variant="secondary" title={b.download_filename || 'gzip'}>
                          gzip
                        </Badge>
                      ) : null}
                    </div>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">
                    {(() => {
                      const uploads = b.storage_uploads ?? []
                      if (!uploads.length) return '—'
                      const ok = uploads.filter((u) => u.ok).length
                      return `${ok}/${uploads.length}`
                    })()}
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">{formatDateTime(b.finished_at)}</td>
                  <td className="py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" className="size-8" asChild>
                        <Link to={`/databases/${b.connection}`}>
                          <Database className="size-4" />
                          <span className="sr-only">Connection</span>
                        </Link>
                      </Button>
                      {b.status === 'in_progress' ? (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-destructive"
                          type="button"
                          disabled={busyId === b.id}
                          title="Stop and remove this in-progress backup"
                          onClick={() => void onCancel(b)}
                        >
                          <Square className="size-4" />
                          <span className="sr-only">Stop</span>
                        </Button>
                      ) : null}
                      {b.status === 'success' ? (
                        <>
                          <Button variant="ghost" size="icon" className="size-8" asChild>
                            <Link to={`/restore?backup=${b.id}`}>
                              <RotateCcw className="size-4" />
                              <span className="sr-only">Restore</span>
                            </Link>
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-8"
                            type="button"
                            onClick={() =>
                              downloadAuthenticated(
                                `/api/backup-records/${b.id}/download/`,
                                b.download_filename || `backup-${b.id}`,
                              ).catch(() => {
                                /* ignore */
                              })
                            }
                          >
                            <Download className="size-4" />
                            <span className="sr-only">Download</span>
                          </Button>
                        </>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && !error ? (
            <p className="py-8 text-center text-muted-foreground">No backup records yet.</p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
