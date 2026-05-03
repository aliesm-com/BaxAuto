import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { LogIn, Pencil, Plus, Trash2 } from 'lucide-react'

import { deleteUser, listUsers, type AdminUserDTO } from '@/api/usersApi'
import { useAuth } from '@/auth/AuthContext'
import { canLoginAs } from '@/auth/access'
import { UserFormModal } from '@/components/users/UserFormModal'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function UsersPage() {
  const { user: current, loginAs } = useAuth()
  const navigate = useNavigate()
  const isAdmin = Boolean(current?.is_superuser || current?.is_admin)

  const [rows, setRows] = useState<AdminUserDTO[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()

  const { modalOpen, editUserId } = useMemo(() => {
    const showNew = searchParams.get('new') === '1'
    const raw = searchParams.get('edit')
    const parsed = raw ? Number(raw) : NaN
    const id = Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
    return { modalOpen: showNew || id != null, editUserId: id }
  }, [searchParams])

  const closeModal = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.delete('new')
      next.delete('edit')
      return next
    })
  }, [setSearchParams])

  const openCreateModal = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('new', '1')
      next.delete('edit')
      return next
    })
  }, [setSearchParams])

  const openEditModal = useCallback(
    (id: number) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        next.delete('new')
        next.set('edit', String(id))
        return next
      })
    },
    [setSearchParams],
  )

  const refresh = useCallback(() => {
    if (!isAdmin) return
    listUsers()
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
  }, [isAdmin])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function onDelete(row: AdminUserDTO) {
    if (row.id === current?.id) {
      window.alert('You cannot delete your own account here.')
      return
    }
    if (row.is_superuser) {
      window.alert('Superuser accounts cannot be deleted from BaxAuto.')
      return
    }
    if (!window.confirm(`Delete user “${row.username}”? This cannot be undone.`)) return
    setBusyId(row.id)
    setError(null)
    try {
      await deleteUser(row.id)
      refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setBusyId(null)
    }
  }

  async function onLoginAs(row: AdminUserDTO) {
    if (!canLoginAs(current) || row.is_superuser || row.id === current?.id) return
    if (
      !window.confirm(
        `Sign in as “${row.username}”? Your current session tokens will be replaced; log out and sign in again as yourself to return.`,
      )
    ) {
      return
    }
    setBusyId(row.id)
    setError(null)
    try {
      await loginAs(row.id)
      navigate('/', { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Login as failed')
    } finally {
      setBusyId(null)
    }
  }

  if (!isAdmin) {
    return (
      <div className="space-y-4 p-6 lg:p-8">
        <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
        <p className="max-w-xl text-sm text-muted-foreground">
          Only superusers or app admins can manage users. Ask an administrator if you need an account created or updated.
        </p>
        <Button variant="outline" asChild>
          <Link to="/settings">Profile settings</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6 lg:p-8">
      <UserFormModal
        open={modalOpen}
        onOpenChange={(open) => {
          if (!open) closeModal()
        }}
        userId={editUserId}
        onSaved={() => refresh()}
      />

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
          <p className="text-sm text-muted-foreground">Create accounts, assign roles, and reset passwords.</p>
        </div>
        <Button type="button" className="rounded-full shadow-md" onClick={openCreateModal}>
          <Plus className="size-4" />
          Add user
        </Button>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle>Accounts</CardTitle>
          <CardDescription>BaxAuto roles only; Django staff/superuser are read-only here.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-3 pr-4 font-medium">Username</th>
                <th className="pb-3 pr-4 font-medium">Email</th>
                <th className="pb-3 pr-4 font-medium">Roles</th>
                <th className="pb-3 pr-4 font-medium">Active</th>
                <th className="pb-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((u) => (
                <tr key={u.id} className="border-b border-border/60 last:border-0">
                  <td className="py-3 pr-4 font-medium">{u.username}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{u.email || '—'}</td>
                  <td className="py-3 pr-4">
                    <div className="flex flex-wrap gap-1">
                      {u.is_superuser ? (
                        <Badge variant="destructive" className="text-[10px]">
                          super
                        </Badge>
                      ) : null}
                      {u.is_admin ? (
                        <Badge variant="secondary" className="text-[10px]">
                          admin
                        </Badge>
                      ) : null}
                      {u.is_staff ? (
                        <Badge variant="outline" className="text-[10px]">
                          staff
                        </Badge>
                      ) : null}
                      {u.is_editor ? (
                        <Badge variant="outline" className="text-[10px]">
                          editor
                        </Badge>
                      ) : null}
                      {u.is_viewer ? (
                        <Badge variant="outline" className="text-[10px]">
                          viewer
                        </Badge>
                      ) : null}
                      {!u.is_superuser && !u.is_admin && !u.is_editor && !u.is_viewer && !u.is_staff ? (
                        <span className="text-muted-foreground">—</span>
                      ) : null}
                    </div>
                  </td>
                  <td className="py-3 pr-4">
                    <Badge variant={u.is_active ? 'success' : 'muted'}>{u.is_active ? 'Yes' : 'No'}</Badge>
                  </td>
                  <td className="py-3 text-right">
                    <div className="flex justify-end gap-1">
                      {canLoginAs(current) && !u.is_superuser && u.id !== current?.id ? (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          title="Sign in as this user"
                          disabled={busyId === u.id}
                          onClick={() => void onLoginAs(u)}
                        >
                          <LogIn className="size-4" />
                          <span className="sr-only">Login as</span>
                        </Button>
                      ) : null}
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="size-8"
                        disabled={u.is_superuser}
                        title={u.is_superuser ? 'Superuser accounts cannot be edited here' : undefined}
                        onClick={() => openEditModal(u.id)}
                      >
                        <Pencil className="size-4" />
                        <span className="sr-only">Edit</span>
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="size-8 text-destructive hover:text-destructive"
                        disabled={busyId === u.id || u.id === current?.id || u.is_superuser}
                        title={u.is_superuser ? 'Superuser accounts cannot be deleted here' : undefined}
                        onClick={() => void onDelete(u)}
                      >
                        <Trash2 className="size-4" />
                        <span className="sr-only">Delete</span>
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && !error ? (
            <p className="py-8 text-center text-muted-foreground">
              No users loaded.{' '}
              <button type="button" className="font-medium text-primary underline-offset-4 hover:underline" onClick={openCreateModal}>
                Add one
              </button>
              .
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
