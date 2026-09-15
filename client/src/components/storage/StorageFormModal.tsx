import { type FormEvent, useEffect, useState } from 'react'

import {
  createStorageDestination,
  getStorageDestination,
  STORAGE_KINDS,
  testStorageDestination,
  updateStorageDestination,
  type StorageDestinationWritePayload,
  type StorageKind,
} from '@/api/storageDestinations'
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

function emptyForm(kind: StorageKind = 's3') {
  return {
    name: '',
    kind,
    host: '',
    port: '',
    username: '',
    secret: '',
    bucket: '',
    region: '',
    endpoint_url: '',
    remote_path: '',
    ftp_passive: true,
    ftp_use_tls: false,
  }
}

export interface StorageFormModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  destinationId?: number
  onSaved?: () => void
}

export function StorageFormModal({ open, onOpenChange, destinationId, onSaved }: StorageFormModalProps) {
  const isEdit = destinationId != null
  const [form, setForm] = useState(emptyForm())
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [testOk, setTestOk] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setError(null)
    setLoadError(null)
    setTestOk(null)

    if (!isEdit) {
      setForm(emptyForm())
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    ;(async () => {
      try {
        const row = await getStorageDestination(destinationId)
        if (cancelled) return
        setForm({
          name: row.name,
          kind: row.kind,
          host: row.host ?? '',
          port: row.port != null ? String(row.port) : '',
          username: row.username ?? '',
          secret: '',
          bucket: row.bucket ?? '',
          region: row.region ?? '',
          endpoint_url: row.endpoint_url ?? '',
          remote_path: row.remote_path ?? '',
          ftp_passive: row.ftp_passive,
          ftp_use_tls: row.ftp_use_tls,
        })
      } catch (e) {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : 'Failed to load')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open, isEdit, destinationId])

  function buildPayload(): StorageDestinationWritePayload {
    const rawPort = form.port.trim()
    const portNum = rawPort === '' ? null : Number(rawPort)
    const kind = form.kind

    const base: StorageDestinationWritePayload = {
      name: form.name.trim(),
      kind,
      host: kind !== 's3' ? form.host.trim() : '',
      port: portNum,
      username: form.username.trim(),
      bucket: kind === 's3' ? form.bucket.trim() : '',
      region: kind === 's3' ? form.region.trim() : '',
      endpoint_url: kind === 's3' ? form.endpoint_url.trim() : '',
      remote_path: kind !== 's3' ? form.remote_path.trim() : '',
      ftp_passive: kind === 'ftp' ? form.ftp_passive : true,
      ftp_use_tls: kind === 'ftp' ? form.ftp_use_tls : false,
    }

    const secret = form.secret.trim()
    if (secret) {
      base.secret = secret
    }
    return base
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    if (!form.name.trim()) {
      setError('Name is required.')
      return
    }

    if (form.port.trim() !== '' && Number.isNaN(Number(form.port))) {
      setError('Port must be a number.')
      return
    }

    if (form.kind !== 's3' && !form.host.trim()) {
      setError('Host is required for SFTP and FTP.')
      return
    }
    if (!form.username.trim()) {
      setError(form.kind === 's3' ? 'Access key ID is required.' : 'Username is required.')
      return
    }
    if (form.kind === 's3' && !form.bucket.trim()) {
      setError('Bucket is required for S3.')
      return
    }

    if (!isEdit && !form.secret.trim()) {
      setError(form.kind === 's3' ? 'Secret access key is required.' : 'Password is required.')
      return
    }

    try {
      const payload = buildPayload()

      setSaving(true)
      if (isEdit && destinationId != null) {
        await updateStorageDestination(destinationId, payload)
      } else {
        await createStorageDestination(payload)
      }
      onSaved?.()
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function onTest() {
    if (destinationId == null) {
      setError('Save the destination first, then test.')
      return
    }
    setError(null)
    setTestOk(null)
    setTesting(true)
    try {
      await testStorageDestination(destinationId)
      setTestOk('Connection succeeded.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Test failed')
    } finally {
      setTesting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[min(90vh,920px)] max-w-xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit storage' : 'Add storage destination'}</DialogTitle>
          <DialogDescription>
            S3-compatible APIs, SFTP, or FTP. Secrets use the same Fernet key as database passwords when configured on the server.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : loadError && isEdit ? (
          <p className="text-sm text-red-600">{loadError}</p>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            {error ? <p className="text-sm text-red-600">{error}</p> : null}
            {testOk ? <p className="text-sm text-emerald-700">{testOk}</p> : null}

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="stor-name">Display name</Label>
                <Input
                  id="stor-name"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  required
                  placeholder="Off-site backups"
                />
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="stor-kind">Type</Label>
                <select
                  id="stor-kind"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={form.kind}
                  onChange={(e) => setForm((f) => ({ ...f, kind: e.target.value as StorageKind }))}
                >
                  {STORAGE_KINDS.map((k) => (
                    <option key={k.value} value={k.value}>
                      {k.label}
                    </option>
                  ))}
                </select>
              </div>

              {form.kind === 's3' ? (
                <>
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="stor-bucket">Bucket</Label>
                    <Input id="stor-bucket" value={form.bucket} onChange={(e) => setForm((f) => ({ ...f, bucket: e.target.value }))} required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="stor-region">Region</Label>
                    <Input id="stor-region" value={form.region} onChange={(e) => setForm((f) => ({ ...f, region: e.target.value }))} placeholder="eu-central-1" />
                  </div>
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="stor-endpoint">Endpoint URL (optional)</Label>
                    <Input
                      id="stor-endpoint"
                      value={form.endpoint_url}
                      onChange={(e) => setForm((f) => ({ ...f, endpoint_url: e.target.value }))}
                      placeholder="https://minio.example.com:9000"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="stor-ak">Access key ID</Label>
                    <Input id="stor-ak" value={form.username} onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))} autoComplete="off" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="stor-sk">{isEdit ? 'Secret key (leave blank to keep)' : 'Secret access key'}</Label>
                    <Input id="stor-sk" type="password" value={form.secret} onChange={(e) => setForm((f) => ({ ...f, secret: e.target.value }))} autoComplete="new-password" />
                  </div>
                </>
              ) : (
                <>
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="stor-host">Host</Label>
                    <Input id="stor-host" value={form.host} onChange={(e) => setForm((f) => ({ ...f, host: e.target.value }))} placeholder="sftp.example.com" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="stor-port">Port</Label>
                    <Input
                      id="stor-port"
                      inputMode="numeric"
                      value={form.port}
                      onChange={(e) => setForm((f) => ({ ...f, port: e.target.value }))}
                      placeholder={form.kind === 'sftp' ? '22' : '21'}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="stor-user">Username</Label>
                    <Input id="stor-user" value={form.username} onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))} autoComplete="off" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="stor-pass">{isEdit ? 'Password (leave blank to keep)' : 'Password'}</Label>
                    <Input id="stor-pass" type="password" value={form.secret} onChange={(e) => setForm((f) => ({ ...f, secret: e.target.value }))} autoComplete="new-password" />
                  </div>
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="stor-path">Remote path</Label>
                    <Input id="stor-path" value={form.remote_path} onChange={(e) => setForm((f) => ({ ...f, remote_path: e.target.value }))} placeholder="/backups/baxauto" />
                  </div>
                  {form.kind === 'ftp' ? (
                    <>
                      <label className="flex cursor-pointer items-center gap-2 sm:col-span-2">
                        <input type="checkbox" checked={form.ftp_passive} onChange={(e) => setForm((f) => ({ ...f, ftp_passive: e.target.checked }))} className="size-4 rounded" />
                        <span className="text-sm font-medium">Passive mode</span>
                      </label>
                      <label className="flex cursor-pointer items-center gap-2 sm:col-span-2">
                        <input type="checkbox" checked={form.ftp_use_tls} onChange={(e) => setForm((f) => ({ ...f, ftp_use_tls: e.target.checked }))} className="size-4 rounded" />
                        <span className="text-sm font-medium">FTP over TLS (FTPS)</span>
                      </label>
                    </>
                  ) : null}
                </>
              )}
            </div>

            <DialogFooter className="gap-2 border-t border-border pt-4 sm:justify-between">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <div className="flex gap-2">
                {isEdit ? (
                  <Button type="button" variant="outline" disabled={testing || saving} onClick={() => void onTest()}>
                    {testing ? 'Testing…' : 'Test connection'}
                  </Button>
                ) : null}
                <Button type="submit" disabled={saving}>
                  {saving ? 'Saving…' : isEdit ? 'Save' : 'Create'}
                </Button>
              </div>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
