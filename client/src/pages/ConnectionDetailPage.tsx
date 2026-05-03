import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { ArrowLeft, Download, Pencil, Share2, Trash2 } from 'lucide-react'

import { deleteConnection, getConnection, triggerBackupDownload, type DatabaseConnectionDTO } from '@/api/dbConnections'
import { ConnectionFormModal } from '@/components/connections/ConnectionFormModal'
import { ConnectionSharesModal } from '@/components/connections/ConnectionSharesModal'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

export function ConnectionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [row, setRow] = useState<DatabaseConnectionDTO | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [shareOpen, setShareOpen] = useState(false)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    ;(async () => {
      try {
        const data = await getConnection(Number(id))
        if (!cancelled) setRow(data)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Not found')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id])

  async function onBackup() {
    if (!id) return
    setBusy(true)
    setError(null)
    try {
      const { blob, filename } = await triggerBackupDownload(Number(id))
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Backup failed')
    } finally {
      setBusy(false)
    }
  }

  async function onDelete() {
    if (!id || !window.confirm('Delete this connection and its saved credentials?')) return
    setBusy(true)
    try {
      await deleteConnection(Number(id))
      navigate('/databases', { replace: true })
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
          <Link to="/databases">
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

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6 lg:p-8">
      <ConnectionFormModal
        open={editOpen}
        onOpenChange={setEditOpen}
        connectionId={row.id}
        onSaved={async () => {
          try {
            const data = await getConnection(Number(id))
            setRow(data)
          } catch {
            /* ignore refresh errors */
          }
        }}
      />
      <ConnectionSharesModal
        open={shareOpen}
        onOpenChange={setShareOpen}
        connectionId={row.id}
        connectionName={row.name}
        onChanged={async () => {
          try {
            const data = await getConnection(Number(id))
            setRow(data)
          } catch {
            /* ignore */
          }
        }}
      />
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/databases">
              <ArrowLeft className="size-5" />
            </Link>
          </Button>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">{row.name}</h1>
              <Badge variant="secondary" className="capitalize">
                {row.engine}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {row.host}:{row.port ?? 'default'} · {row.database_name || '—'}
            </p>
            {row.access_role !== 'owner' ? (
              <p className="mt-1 text-xs text-muted-foreground">
                Owner @{row.owner_username} · Your role: <span className="capitalize">{row.access_role}</span>
              </p>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {row.access_role === 'owner' ? (
            <Button variant="outline" size="sm" type="button" onClick={() => setShareOpen(true)}>
              <Share2 className="mr-2 size-4" />
              Share
            </Button>
          ) : null}
          <Button
            variant="outline"
            size="sm"
            type="button"
            disabled={row.access_role === 'viewer'}
            title={row.access_role === 'viewer' ? 'Viewers cannot edit this connection' : undefined}
            onClick={() => setEditOpen(true)}
          >
            <Pencil className="mr-2 size-4" />
            Edit
          </Button>
          <Button
            size="sm"
            disabled={busy || row.access_role === 'viewer'}
            title={row.access_role === 'viewer' ? 'Viewers cannot run backups' : undefined}
            onClick={() => void onBackup()}
          >
            <Download className="mr-2 size-4" />
            Run backup
          </Button>
          <Button
            variant="destructive"
            size="sm"
            disabled={busy || row.access_role !== 'owner'}
            title={row.access_role !== 'owner' ? 'Only the owner can delete this connection' : undefined}
            onClick={() => void onDelete()}
          >
            <Trash2 className="mr-2 size-4" />
            Delete
          </Button>
        </div>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle>Parameters</CardTitle>
          <CardDescription>Values used by backup / restore drivers.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <p className="text-muted-foreground">Username</p>
              <p className="font-medium">{row.username || '—'}</p>
            </div>
            <div>
              <p className="text-muted-foreground">TLS</p>
              <p className="font-medium">{row.use_tls ? 'Yes' : 'No'}</p>
            </div>
            {row.engine === 'rabbitmq' ? (
              <div>
                <p className="text-muted-foreground">Virtual host</p>
                <p className="font-medium">{row.virtual_host || '/'}</p>
              </div>
            ) : null}
          </div>
          {row.connection_uri ? (
            <>
              <Separator />
              <div>
                <p className="text-muted-foreground">URI</p>
                <p className="break-all font-mono text-xs">{row.connection_uri}</p>
              </div>
            </>
          ) : null}
          <Separator />
          <div>
            <p className="text-muted-foreground">Extra options</p>
            <pre className="mt-1 overflow-x-auto rounded-lg bg-muted p-3 font-mono text-xs">
              {JSON.stringify(row.extra_options ?? {}, null, 2)}
            </pre>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
