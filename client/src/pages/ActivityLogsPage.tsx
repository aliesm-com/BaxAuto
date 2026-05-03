import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Database } from 'lucide-react'

import type { RestoreRecordDTO } from '@/api/restoresApi'
import { listRestoreRecords } from '@/api/restoresApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function ActivityLogsPage() {
  const [rows, setRows] = useState<RestoreRecordDTO[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listRestoreRecords()
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
  }, [])

  return (
    <div className="space-y-6 p-6 lg:p-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Activity Logs</h1>
        <p className="text-sm text-muted-foreground">Restore attempts for your database connections (audit trail from the API).</p>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle>Restore history</CardTitle>
          <CardDescription>Each row links to the connection used when the restore ran.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-3 pr-4 font-medium">ID</th>
                <th className="pb-3 pr-4 font-medium">Backup</th>
                <th className="pb-3 pr-4 font-medium">Engine</th>
                <th className="pb-3 pr-4 font-medium">Status</th>
                <th className="pb-3 pr-4 font-medium">By</th>
                <th className="pb-3 pr-4 font-medium">Started</th>
                <th className="pb-3 pr-4 font-medium max-w-[200px]">Note</th>
                <th className="pb-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-border/60 last:border-0">
                  <td className="py-3 pr-4 font-mono text-xs">#{r.id}</td>
                  <td className="py-3 pr-4 font-mono text-xs">{r.backup}</td>
                  <td className="py-3 pr-4 capitalize">{r.engine}</td>
                  <td className="py-3 pr-4">
                    <Badge variant={r.status === 'success' ? 'success' : r.status === 'failed' ? 'destructive' : 'muted'}>{r.status}</Badge>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">{r.initiated_by_username ?? '—'}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{r.created_at}</td>
                  <td className="max-w-[200px] truncate py-3 pr-4 text-xs text-muted-foreground" title={r.error_message || undefined}>
                    {r.error_message ? r.error_message.slice(0, 80) + (r.error_message.length > 80 ? '…' : '') : '—'}
                  </td>
                  <td className="py-3 text-right">
                    <Button variant="ghost" size="icon" className="size-8" asChild>
                      <Link to={`/databases/${r.connection}`}>
                        <Database className="size-4" />
                        <span className="sr-only">Connection</span>
                      </Link>
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && !error ? <p className="py-8 text-center text-muted-foreground">No restore activity yet.</p> : null}
        </CardContent>
      </Card>
    </div>
  )
}
