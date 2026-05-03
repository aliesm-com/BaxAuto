import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Database, Download, RotateCcw } from 'lucide-react'

import type { BackupRecord } from '@/api/resources'
import { listBackupRecords } from '@/api/resources'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { downloadAuthenticated } from '@/lib/download'

export function BackupRecordsPage() {
  const [rows, setRows] = useState<BackupRecord[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listBackupRecords()
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
  }, [])

  return (
    <div className="space-y-6 p-6 lg:p-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Backups</h1>
        <p className="text-sm text-muted-foreground">Logical backups recorded for your connections.</p>
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
                    <Badge variant={b.status === 'success' ? 'success' : b.status === 'failed' ? 'destructive' : 'muted'}>
                      {b.status}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">{b.finished_at ?? '—'}</td>
                  <td className="py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" className="size-8" asChild>
                        <Link to={`/databases/${b.connection}`}>
                          <Database className="size-4" />
                          <span className="sr-only">Connection</span>
                        </Link>
                      </Button>
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
