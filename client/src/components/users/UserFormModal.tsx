import { type FormEvent, useEffect, useState } from 'react'

import { createUser, getUser, updateUser, type AdminUserWritePayload } from '@/api/usersApi'
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

export interface UserFormModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  userId?: number
  onSaved?: () => void
}

function emptyForm() {
  return {
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    is_active: true,
    is_viewer: false,
    is_editor: false,
    is_admin: false,
    phone_number: '',
    country_code: '',
  }
}

export function UserFormModal({ open, onOpenChange, userId, onSaved }: UserFormModalProps) {
  const isEdit = userId != null
  const [form, setForm] = useState(emptyForm())
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [blockedSuperuser, setBlockedSuperuser] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setError(null)
    setLoadError(null)
    setBlockedSuperuser(false)

    if (!isEdit) {
      setForm(emptyForm())
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    ;(async () => {
      try {
        const u = await getUser(userId)
        if (cancelled) return
        if (u.is_superuser) {
          setBlockedSuperuser(true)
          setForm(emptyForm())
          return
        }
        setForm({
          username: u.username,
          email: u.email ?? '',
          first_name: u.first_name ?? '',
          last_name: u.last_name ?? '',
          password: '',
          is_active: u.is_active,
          is_viewer: u.is_viewer,
          is_editor: u.is_editor,
          is_admin: u.is_admin,
          phone_number: u.phone_number ?? '',
          country_code: u.country_code ?? '',
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
  }, [open, isEdit, userId])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    if (blockedSuperuser) return

    if (!form.username.trim()) {
      setError('Username is required.')
      return
    }

    const payload: AdminUserWritePayload = {
      username: form.username.trim(),
      email: form.email.trim(),
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      is_active: form.is_active,
      is_viewer: form.is_viewer,
      is_editor: form.is_editor,
      is_admin: form.is_admin,
      phone_number: form.phone_number.trim() || null,
      country_code: form.country_code.trim() || null,
    }

    if (!isEdit) {
      if (!form.password.trim() || form.password.length < 8) {
        setError('Password must be at least 8 characters.')
        return
      }
      payload.password = form.password
    } else if (form.password.trim()) {
      if (form.password.length < 8) {
        setError('New password must be at least 8 characters.')
        return
      }
      payload.password = form.password
    }

    setSaving(true)
    try {
      if (isEdit && userId != null) {
        await updateUser(userId, payload)
      } else {
        await createUser(payload)
      }
      onSaved?.()
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[min(90vh,900px)] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit user' : 'Create user'}</DialogTitle>
          <DialogDescription>
            BaxAuto roles only — Django staff/superuser are managed outside this screen (e.g.{' '}
            <code className="text-xs">manage.py createsuperuser</code> / Django admin).
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : loadError && isEdit ? (
          <p className="text-sm text-red-600">{loadError}</p>
        ) : blockedSuperuser ? (
          <>
            <p className="text-sm text-muted-foreground">
              This account is a Django superuser. It cannot be edited or deleted from BaxAuto — use Django&apos;s admin
              interface instead.
            </p>
            <DialogFooter className="border-t border-border pt-4">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Close
              </Button>
            </DialogFooter>
          </>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            {error ? <p className="text-sm text-red-600">{error}</p> : null}

            <div className="space-y-2">
              <Label htmlFor="usr-username">Username</Label>
              <Input
                id="usr-username"
                value={form.username}
                onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                required
                autoComplete="off"
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="usr-email">Email</Label>
                <Input id="usr-email" type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="usr-pass">{isEdit ? 'New password (optional)' : 'Password'}</Label>
                <Input
                  id="usr-pass"
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                  autoComplete="new-password"
                  placeholder={isEdit ? 'Leave blank to keep current' : 'Minimum 8 characters'}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="usr-fn">First name</Label>
                <Input id="usr-fn" value={form.first_name} onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="usr-ln">Last name</Label>
                <Input id="usr-ln" value={form.last_name} onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="usr-phone">Phone</Label>
                <Input id="usr-phone" value={form.phone_number} onChange={(e) => setForm((f) => ({ ...f, phone_number: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="usr-cc">Country code</Label>
                <Input id="usr-cc" value={form.country_code} onChange={(e) => setForm((f) => ({ ...f, country_code: e.target.value }))} placeholder="+98" />
              </div>
            </div>

            <div className="space-y-2 rounded-lg border border-border bg-muted/30 p-3">
              <p className="text-xs font-medium text-muted-foreground">Roles</p>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} className="size-4 rounded" />
                <span className="text-sm">Active</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={form.is_admin} onChange={(e) => setForm((f) => ({ ...f, is_admin: e.target.checked }))} className="size-4 rounded" />
                <span className="text-sm">App admin (users &amp; schedules)</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={form.is_editor} onChange={(e) => setForm((f) => ({ ...f, is_editor: e.target.checked }))} className="size-4 rounded" />
                <span className="text-sm">Editor</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={form.is_viewer} onChange={(e) => setForm((f) => ({ ...f, is_viewer: e.target.checked }))} className="size-4 rounded" />
                <span className="text-sm">Viewer (read-only)</span>
              </label>
            </div>

            <DialogFooter className="gap-2 border-t border-border pt-4 sm:justify-between">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving…' : isEdit ? 'Save user' : 'Create user'}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
