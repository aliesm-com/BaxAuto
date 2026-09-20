import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { ArrowLeft, Download, Pencil, PlugZap, Share2, Trash2 } from 'lucide-react'

import {
  deleteConnection,
  getConnection,
  testConnection,
  triggerBackupDownload,
  type ConnectionProbeResult,
  type DatabaseConnectionDTO,
} from '@/api/dbConnections'
import { ConnectionFormModal } from '@/components/connections/ConnectionFormModal'
import { ConnectionSharesModal } from '@/components/connections/ConnectionSharesModal'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

function probeBadge(ok: boolean | null | undefined) {
  if (ok === true) return <Badge className="bg-emerald-600 hover:bg-emerald-600">OK</Badge>
  if (ok === false) return <Badge variant="destructive">Failed</Badge>
  return <Badge variant="outline">Skipped</Badge>
}

export function ConnectionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [row, setRow] = useState<DatabaseConnectionDTO | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [testing, setTesting] = useState(false)
  const [probe, setProbe] = useState<ConnectionProbeResult | null>(null)
  const [editOpen, setEditOpen] = useState(false)
  const [shareOpen, setShareOpen] = useState(false)
  const [compress, setCompress] = useState(false)

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

  async function onTest() {
    if (!id) return
    setTesting(true)
    setError(null)
    try {
      const result = await testConnection(Number(id))
      setProbe(result)
      if (!result.ok) {
        setError(result.detail || 'Connection test failed')
      }
    } catch (e) {
      setProbe(null)
      setError(e instanceof Error ? e.message : 'Connection test failed')
    } finally {
      setTesting(false)
    }
  }

  async function onBackup() {
    if (!id) return
    setBusy(true)
    setError(null)
    try {
      const { blob, filename } = await triggerBackupDownload(Number(id), { compress })
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
            setProbe(null)
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
              {row.ssh_enabled ? ` · SSH via ${row.ssh_host || '—'}` : ''}
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
            variant="outline"
            size="sm"
            type="button"
            disabled={testing || busy || row.access_role === 'viewer'}
            title={row.access_role === 'viewer' ? 'Viewers cannot run connection tests' : undefined}
            onClick={() => void onTest()}
          >
            <PlugZap className="mr-2 size-4" />
            {testing ? 'Testing…' : 'Test connection'}
          </Button>
          <label className="flex items-center gap-2 text-sm" title="Also copies the dump to every storage destination on your account">
            <input
              type="checkbox"
              className="size-4 rounded"
              checked={compress}
              disabled={busy || row.access_role === 'viewer'}
              onChange={(e) => setCompress(e.target.checked)}
            />
            Compress (gzip)
          </label>
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

      {probe ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Test result
              {probe.ok ? (
                <Badge className="bg-emerald-600 hover:bg-emerald-600">All OK</Badge>
              ) : (
                <Badge variant="destructive">Failed</Badge>
              )}
            </CardTitle>
            <CardDescription>SSH tunnel and database are checked as separate steps.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="space-y-1">
              <div className="flex items-center gap-2 font-medium">
                SSH tunnel
                {probeBadge(probe.ssh.enabled === false ? true : probe.ssh.ok)}
                {probe.ssh.enabled === false ? (
                  <span className="text-xs font-normal text-muted-foreground">(not used)</span>
                ) : null}
              </div>
              <p className="text-muted-foreground">{probe.ssh.detail || '—'}</p>
            </div>
            <Separator />
            <div className="space-y-1">
              <div className="flex items-center gap-2 font-medium">
                Database
                {probeBadge(probe.database.ok)}
              </div>
              <p className="text-muted-foreground">{probe.database.detail || '—'}</p>
            </div>
          </CardContent>
        </Card>
      ) : null}

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
            <div>
              <p className="text-muted-foreground">SSH tunnel</p>
              <p className="font-medium">{row.ssh_enabled ? 'Enabled' : 'Off'}</p>
            </div>
            {row.ssh_enabled ? (
              <>
                <div>
                  <p className="text-muted-foreground">SSH host</p>
                  <p className="font-medium">
                    {row.ssh_username}@{row.ssh_host}:{row.ssh_port ?? 22}
                  </p>
                </div>
                <div className="sm:col-span-2">
                  <p className="text-muted-foreground">Host key fingerprint</p>
                  <p className="break-all font-mono text-xs">{row.ssh_host_key_fingerprint || '—'}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">SSH auth</p>
                  <p className="font-medium">
                    {[
                      row.ssh_private_key_set ? 'private key' : null,
                      row.ssh_password_set ? 'password' : null,
                    ]
                      .filter(Boolean)
                      .join(' + ') || '—'}
                  </p>
                </div>
              </>
            ) : null}
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
