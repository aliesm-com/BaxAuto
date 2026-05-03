import { type FormEvent, useEffect, useState } from 'react'

import { Trash2 } from 'lucide-react'

import {
  addConnectionShare,
  listConnectionShares,
  removeConnectionShare,
  type ConnectionShareDTO,
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

export interface ConnectionSharesModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  connectionId: number | null
  connectionName?: string
  onChanged?: () => void
}

export function ConnectionSharesModal({
  open,
  onOpenChange,
  connectionId,
  connectionName,
  onChanged,
}: ConnectionSharesModalProps) {
  const [rows, setRows] = useState<ConnectionShareDTO[]>([])
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [userIdRaw, setUserIdRaw] = useState('')
  const [role, setRole] = useState<'viewer' | 'editor'>('viewer')
  const [busyUser, setBusyUser] = useState<number | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (!open || connectionId == null) return
    setLoadError(null)
    setFormError(null)
    let cancelled = false
    setLoading(true)
    listConnectionShares(connectionId)
      .then((r) => {
        if (!cancelled) setRows(r)
      })
      .catch((e) => {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : 'Failed to load shares')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, connectionId])

  async function onAdd(e: FormEvent) {
    e.preventDefault()
    setFormError(null)
    if (connectionId == null) return
    const uid = Number(userIdRaw.trim())
    if (!Number.isInteger(uid) || uid <= 0) {
      setFormError('Enter a positive numeric user ID.')
      return
    }
    try {
      await addConnectionShare(connectionId, { user: uid, role })
      setUserIdRaw('')
      const next = await listConnectionShares(connectionId)
      setRows(next)
      onChanged?.()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Could not add share')
    }
  }

  async function onRemove(memberUserId: number) {
    if (connectionId == null) return
    if (!window.confirm('Remove this user’s access to this connection?')) return
    setBusyUser(memberUserId)
    try {
      await removeConnectionShare(connectionId, memberUserId)
      const next = await listConnectionShares(connectionId)
      setRows(next)
      onChanged?.()
    } catch (err) {
      window.alert(err instanceof Error ? err.message : 'Remove failed')
    } finally {
      setBusyUser(null)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Share connection</DialogTitle>
          <DialogDescription>
            Grant another BaxAuto user access by their numeric user ID (shown on Settings → Profile). Owner:{' '}
            <span className="font-medium text-foreground">{connectionName ?? `#${connectionId ?? ''}`}</span>
          </DialogDescription>
        </DialogHeader>

        {loading ? <p className="text-sm text-muted-foreground">Loading…</p> : null}
        {loadError ? <p className="text-sm text-red-600">{loadError}</p> : null}

        <form onSubmit={onAdd} className="space-y-3 rounded-lg border border-border bg-muted/20 p-3">
          <p className="text-xs font-medium text-muted-foreground">Add member</p>
          {formError ? <p className="text-xs text-red-600">{formError}</p> : null}
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="share-uid">User ID</Label>
              <Input
                id="share-uid"
                inputMode="numeric"
                value={userIdRaw}
                onChange={(e) => setUserIdRaw(e.target.value)}
                placeholder="e.g. 3"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="share-role">Role</Label>
              <select
                id="share-role"
                value={role}
                onChange={(e) => setRole(e.target.value as 'viewer' | 'editor')}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="viewer">Viewer — view &amp; download backups</option>
                <option value="editor">Editor — edit connection, backup, test</option>
              </select>
            </div>
          </div>
          <Button type="submit" size="sm" disabled={connectionId == null}>
            Add or update access
          </Button>
        </form>

        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">People with access</p>
          {rows.length === 0 && !loading ? (
            <p className="text-sm text-muted-foreground">No extra members yet.</p>
          ) : (
            <ul className="divide-y divide-border rounded-md border border-border text-sm">
              {rows.map((s) => (
                <li key={s.user} className="flex items-center justify-between gap-2 px-3 py-2">
                  <span>
                    <span className="font-medium">@{s.username}</span>
                    <span className="text-muted-foreground"> · ID {s.user} · </span>
                    <span className="capitalize text-muted-foreground">{s.role}</span>
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="size-8 text-destructive"
                    disabled={busyUser === s.user}
                    onClick={() => void onRemove(s.user)}
                  >
                    <Trash2 className="size-4" />
                    <span className="sr-only">Remove</span>
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
