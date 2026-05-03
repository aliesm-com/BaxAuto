import { type FormEvent, useEffect, useState } from 'react'

import {
  ENGINES,
  createConnection,
  getConnection,
  updateConnection,
  type ConnectionWritePayload,
} from '@/api/dbConnections'
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

function emptyForm() {
  return {
    name: '',
    engine: 'postgresql',
    host: '',
    port: '',
    database_name: '',
    username: '',
    password: '',
    virtual_host: '/',
    connection_uri: '',
    use_tls: false,
    extra_options: '{}',
  }
}

export interface ConnectionFormModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** When set, modal edits this connection; otherwise creates a new one. */
  connectionId?: number
  onSaved?: (detail: { id: number; mode: 'create' | 'edit' }) => void
}

export function ConnectionFormModal({ open, onOpenChange, connectionId, onSaved }: ConnectionFormModalProps) {
  const isEdit = connectionId != null
  const [form, setForm] = useState(emptyForm)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setError(null)
    if (!isEdit) {
      setForm(emptyForm())
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    ;(async () => {
      try {
        const row = await getConnection(connectionId)
        if (cancelled) return
        setForm({
          name: row.name,
          engine: row.engine,
          host: row.host ?? '',
          port: row.port != null ? String(row.port) : '',
          database_name: row.database_name ?? '',
          username: row.username ?? '',
          password: '',
          virtual_host: row.virtual_host ?? '/',
          connection_uri: row.connection_uri ?? '',
          use_tls: row.use_tls,
          extra_options: JSON.stringify(row.extra_options ?? {}, null, 2),
        })
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open, isEdit, connectionId])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    let extra: Record<string, unknown> = {}
    try {
      extra = form.extra_options.trim() ? (JSON.parse(form.extra_options) as Record<string, unknown>) : {}
    } catch {
      setError('Extra options must be valid JSON.')
      return
    }

    const portNum = form.port.trim() === '' ? null : Number(form.port)
    if (form.port.trim() !== '' && Number.isNaN(portNum)) {
      setError('Port must be a number.')
      return
    }

    const payload: ConnectionWritePayload = {
      name: form.name.trim(),
      engine: form.engine,
      host: form.host.trim(),
      port: portNum,
      database_name: form.database_name.trim(),
      username: form.username.trim(),
      virtual_host: form.virtual_host.trim(),
      connection_uri: form.connection_uri.trim(),
      use_tls: form.use_tls,
      extra_options: extra,
    }

    if (form.password.trim()) {
      payload.password = form.password
    }

    setSaving(true)
    try {
      if (isEdit && connectionId != null) {
        const patch: Partial<ConnectionWritePayload> = { ...payload }
        if (!form.password.trim()) delete patch.password
        await updateConnection(connectionId, patch)
        onSaved?.({ id: connectionId, mode: 'edit' })
      } else {
        const created = await createConnection(payload)
        onSaved?.({ id: created.id, mode: 'create' })
      }
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const engineNeedsUri = form.engine === 'mongodb'
  const engineRabbit = form.engine === 'rabbitmq'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[min(90vh,880px)] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit connection' : 'Add database'}</DialogTitle>
          <DialogDescription>
            Credentials are stored encrypted on the server when{' '}
            <code className="text-xs">DB_CREDENTIALS_FERNET_KEY</code> is set.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            {error ? <p className="text-sm text-red-600">{error}</p> : null}

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="conn-modal-name">Display name</Label>
                <Input
                  id="conn-modal-name"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  required
                  placeholder="Production DB"
                />
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="conn-modal-engine">Engine</Label>
                <select
                  id="conn-modal-engine"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={form.engine}
                  onChange={(e) => setForm((f) => ({ ...f, engine: e.target.value }))}
                >
                  {ENGINES.map((en) => (
                    <option key={en.value} value={en.value}>
                      {en.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="conn-modal-uri">Connection URI (optional)</Label>
                <Input
                  id="conn-modal-uri"
                  value={form.connection_uri}
                  onChange={(e) => setForm((f) => ({ ...f, connection_uri: e.target.value }))}
                  placeholder="mongodb://… or leave empty"
                  autoComplete="off"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="conn-modal-host">Host</Label>
                <Input
                  id="conn-modal-host"
                  value={form.host}
                  onChange={(e) => setForm((f) => ({ ...f, host: e.target.value }))}
                  placeholder="127.0.0.1"
                  required={!engineNeedsUri || !form.connection_uri.trim()}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="conn-modal-port">Port</Label>
                <Input
                  id="conn-modal-port"
                  value={form.port}
                  onChange={(e) => setForm((f) => ({ ...f, port: e.target.value }))}
                  placeholder="default"
                  inputMode="numeric"
                />
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="conn-modal-db">Database / logical DB / schema name</Label>
                <Input
                  id="conn-modal-db"
                  value={form.database_name}
                  onChange={(e) => setForm((f) => ({ ...f, database_name: e.target.value }))}
                  placeholder="postgres, 0 for Redis, etc."
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="conn-modal-user">Username</Label>
                <Input
                  id="conn-modal-user"
                  value={form.username}
                  onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                  autoComplete="off"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="conn-modal-pass">Password</Label>
                <Input
                  id="conn-modal-pass"
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                  placeholder={isEdit ? '(unchanged if empty)' : ''}
                  autoComplete="new-password"
                />
              </div>

              {engineRabbit ? (
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="conn-modal-vhost">RabbitMQ virtual host</Label>
                  <Input
                    id="conn-modal-vhost"
                    value={form.virtual_host}
                    onChange={(e) => setForm((f) => ({ ...f, virtual_host: e.target.value }))}
                    placeholder="/"
                  />
                </div>
              ) : null}

              <label className="flex cursor-pointer items-center gap-2 sm:col-span-2">
                <input
                  type="checkbox"
                  checked={form.use_tls}
                  onChange={(e) => setForm((f) => ({ ...f, use_tls: e.target.checked }))}
                  className="size-4 rounded border-input"
                />
                <span className="text-sm font-medium">Use TLS / SSL</span>
              </label>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="conn-modal-extra">Extra options (JSON)</Label>
                <Textarea
                  id="conn-modal-extra"
                  value={form.extra_options}
                  onChange={(e) => setForm((f) => ({ ...f, extra_options: e.target.value }))}
                  rows={5}
                  className="font-mono text-xs"
                  placeholder='{"authSource": "admin"}'
                />
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              {engineNeedsUri
                ? 'MongoDB: provide a URI or host-based settings.'
                : 'Host is required unless your engine allows URI-only configuration.'}
            </p>

            <DialogFooter className="gap-2 border-t border-border pt-4 sm:justify-between">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Create connection'}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
