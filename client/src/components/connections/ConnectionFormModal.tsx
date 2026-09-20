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
    ssh_enabled: false,
    ssh_host: '',
    ssh_port: '22',
    ssh_username: '',
    ssh_password: '',
    ssh_private_key: '',
    ssh_private_key_passphrase: '',
    ssh_host_key_fingerprint: '',
    ssh_private_key_set: false,
    ssh_password_set: false,
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
          ssh_enabled: Boolean(row.ssh_enabled),
          ssh_host: row.ssh_host ?? '',
          ssh_port: row.ssh_port != null ? String(row.ssh_port) : '22',
          ssh_username: row.ssh_username ?? '',
          ssh_password: '',
          ssh_private_key: '',
          ssh_private_key_passphrase: '',
          ssh_host_key_fingerprint: row.ssh_host_key_fingerprint ?? '',
          ssh_private_key_set: Boolean(row.ssh_private_key_set),
          ssh_password_set: Boolean(row.ssh_password_set),
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

    const sshPortNum = form.ssh_port.trim() === '' ? 22 : Number(form.ssh_port)
    if (form.ssh_enabled && Number.isNaN(sshPortNum)) {
      setError('SSH port must be a number.')
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
      connection_uri: form.ssh_enabled ? '' : form.connection_uri.trim(),
      use_tls: form.use_tls,
      ssh_enabled: form.ssh_enabled,
      ssh_host: form.ssh_host.trim(),
      ssh_port: form.ssh_enabled ? sshPortNum : null,
      ssh_username: form.ssh_username.trim(),
      ssh_host_key_fingerprint: form.ssh_host_key_fingerprint.trim(),
      extra_options: extra,
    }

    if (form.password.trim()) {
      payload.password = form.password
    }
    if (form.ssh_password.trim()) {
      payload.ssh_password = form.ssh_password
    }
    if (form.ssh_private_key.trim()) {
      payload.ssh_private_key = form.ssh_private_key
    }
    if (form.ssh_private_key_passphrase.trim()) {
      payload.ssh_private_key_passphrase = form.ssh_private_key_passphrase
    }

    setSaving(true)
    try {
      if (isEdit && connectionId != null) {
        const patch: Partial<ConnectionWritePayload> = { ...payload }
        if (!form.password.trim()) delete patch.password
        if (!form.ssh_password.trim()) delete patch.ssh_password
        if (!form.ssh_private_key.trim()) delete patch.ssh_private_key
        if (!form.ssh_private_key_passphrase.trim()) delete patch.ssh_private_key_passphrase
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

  const engineNeedsUri = form.engine === 'mongodb' && !form.ssh_enabled
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

              {!form.ssh_enabled ? (
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
              ) : null}

              <div className="space-y-2">
                <Label htmlFor="conn-modal-host">
                  {form.ssh_enabled ? 'DB host (from SSH server)' : 'Host'}
                </Label>
                <Input
                  id="conn-modal-host"
                  value={form.host}
                  onChange={(e) => setForm((f) => ({ ...f, host: e.target.value }))}
                  placeholder={form.ssh_enabled ? '127.0.0.1' : 'db.example.com'}
                  required={!engineNeedsUri || !form.connection_uri.trim()}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="conn-modal-port">Port</Label>
                <Input
                  id="conn-modal-port"
                  value={form.port}
                  onChange={(e) => setForm((f) => ({ ...f, port: e.target.value }))}
                  placeholder="5432"
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

              <div className="sm:col-span-2 space-y-3 rounded-md border border-border p-3">
                <label className="flex cursor-pointer items-center gap-2">
                  <input
                    type="checkbox"
                    checked={form.ssh_enabled}
                    onChange={(e) => setForm((f) => ({ ...f, ssh_enabled: e.target.checked }))}
                    className="size-4 rounded border-input"
                  />
                  <span className="text-sm font-medium">SSH tunnel</span>
                </label>
                <p className="text-xs text-muted-foreground">
                  Forward the remote DB (often bound to 127.0.0.1) through SSH. Prefer a dedicated
                  key; host key fingerprint is required for safety.
                </p>
                {form.ssh_enabled ? (
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="conn-modal-ssh-host">SSH host</Label>
                      <Input
                        id="conn-modal-ssh-host"
                        value={form.ssh_host}
                        onChange={(e) => setForm((f) => ({ ...f, ssh_host: e.target.value }))}
                        placeholder="bastion.example.com"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="conn-modal-ssh-port">SSH port</Label>
                      <Input
                        id="conn-modal-ssh-port"
                        value={form.ssh_port}
                        onChange={(e) => setForm((f) => ({ ...f, ssh_port: e.target.value }))}
                        placeholder="22"
                        inputMode="numeric"
                      />
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label htmlFor="conn-modal-ssh-user">SSH username</Label>
                      <Input
                        id="conn-modal-ssh-user"
                        value={form.ssh_username}
                        onChange={(e) => setForm((f) => ({ ...f, ssh_username: e.target.value }))}
                        required
                        autoComplete="off"
                      />
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label htmlFor="conn-modal-ssh-fp">Host key fingerprint (SHA256)</Label>
                      <Input
                        id="conn-modal-ssh-fp"
                        value={form.ssh_host_key_fingerprint}
                        onChange={(e) =>
                          setForm((f) => ({ ...f, ssh_host_key_fingerprint: e.target.value }))
                        }
                        placeholder="SHA256:…"
                        required
                        className="font-mono text-xs"
                      />
                      <p className="text-xs text-muted-foreground">
                        <code className="text-[11px]">ssh-keyscan -t ed25519,rsa HOST | ssh-keygen -lf -</code>
                      </p>
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label htmlFor="conn-modal-ssh-key">
                        Private key (PEM)
                        {isEdit && form.ssh_private_key_set ? ' — leave empty to keep' : ''}
                      </Label>
                      <Textarea
                        id="conn-modal-ssh-key"
                        value={form.ssh_private_key}
                        onChange={(e) => setForm((f) => ({ ...f, ssh_private_key: e.target.value }))}
                        rows={4}
                        className="font-mono text-xs"
                        placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
                        autoComplete="off"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="conn-modal-ssh-key-pass">Key passphrase</Label>
                      <Input
                        id="conn-modal-ssh-key-pass"
                        type="password"
                        value={form.ssh_private_key_passphrase}
                        onChange={(e) =>
                          setForm((f) => ({ ...f, ssh_private_key_passphrase: e.target.value }))
                        }
                        placeholder={isEdit ? '(unchanged if empty)' : 'optional'}
                        autoComplete="new-password"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="conn-modal-ssh-pass">
                        SSH password
                        {isEdit && form.ssh_password_set ? ' — leave empty to keep' : ''}
                      </Label>
                      <Input
                        id="conn-modal-ssh-pass"
                        type="password"
                        value={form.ssh_password}
                        onChange={(e) => setForm((f) => ({ ...f, ssh_password: e.target.value }))}
                        placeholder="optional if using a key"
                        autoComplete="new-password"
                      />
                    </div>
                  </div>
                ) : null}
              </div>

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
              {form.ssh_enabled
                ? 'SSH tunnel: set DB host to the address on the remote machine (usually 127.0.0.1).'
                : engineNeedsUri
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
