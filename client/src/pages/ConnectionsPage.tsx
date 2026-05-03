import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { Eye, Pencil, Plus, Share2, Trash2 } from 'lucide-react'

import type { DatabaseConnectionDTO } from '@/api/dbConnections'
import { deleteConnection, listConnections } from '@/api/dbConnections'
import { ConnectionFormModal } from '@/components/connections/ConnectionFormModal'
import { ConnectionSharesModal } from '@/components/connections/ConnectionSharesModal'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function ConnectionsPage() {
  const [rows, setRows] = useState<DatabaseConnectionDTO[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [shareTarget, setShareTarget] = useState<{ id: number; name: string } | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()

  const { modalOpen, connectionId } = useMemo(() => {
    const showNew = searchParams.get('new') === '1'
    const raw = searchParams.get('edit')
    const parsed = raw ? Number(raw) : NaN
    const editId = Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
    return {
      modalOpen: showNew || editId != null,
      connectionId: editId,
    }
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
    listConnections()
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function onDelete(row: DatabaseConnectionDTO) {
    if (!window.confirm(`Delete connection “${row.name}”?`)) return
    setBusyId(row.id)
    setError(null)
    try {
      await deleteConnection(row.id)
      refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="space-y-6 p-6 lg:p-8">
      <ConnectionFormModal
        open={modalOpen}
        onOpenChange={(open) => {
          if (!open) closeModal()
        }}
        connectionId={connectionId}
        onSaved={() => refresh()}
      />
      <ConnectionSharesModal
        open={shareTarget != null}
        onOpenChange={(open) => {
          if (!open) setShareTarget(null)
        }}
        connectionId={shareTarget?.id ?? null}
        connectionName={shareTarget?.name}
        onChanged={() => refresh()}
      />

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Databases</h1>
          <p className="text-sm text-muted-foreground">
            Your connections and items shared with you. Owners can invite others by user ID.
          </p>
        </div>
        <Button type="button" className="rounded-full shadow-md" onClick={openCreateModal}>
          <Plus className="size-4" />
          Add database
        </Button>
      </div>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <Card>
        <CardHeader>
          <CardTitle>Connections</CardTitle>
          <CardDescription>Open details for backup/download, or use actions for quick edit/delete.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-3 pr-4 font-medium">Name</th>
                <th className="pb-3 pr-4 font-medium">Your access</th>
                <th className="pb-3 pr-4 font-medium">Engine</th>
                <th className="pb-3 pr-4 font-medium">Host</th>
                <th className="pb-3 pr-4 font-medium">Port</th>
                <th className="pb-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id} className="border-b border-border/60 last:border-0">
                  <td className="py-3 pr-4 font-medium">
                    <Link to={`/databases/${c.id}`} className="text-primary hover:underline">
                      {c.name}
                    </Link>
                  </td>
                  <td className="py-3 pr-4">
                    <Badge variant={c.access_role === 'owner' ? 'secondary' : 'outline'} className="text-[10px] capitalize">
                      {c.access_role}
                      {c.access_role !== 'owner' ? (
                        <span className="ml-1 font-normal text-muted-foreground">(@{c.owner_username})</span>
                      ) : null}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4">
                    <Badge variant="secondary" className="capitalize">
                      {c.engine}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4">{c.host}</td>
                  <td className="py-3 pr-4">{c.port ?? '—'}</td>
                  <td className="py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" className="size-8" asChild>
                        <Link to={`/databases/${c.id}`}>
                          <Eye className="size-4" />
                          <span className="sr-only">View</span>
                        </Link>
                      </Button>
                      {c.access_role === 'owner' ? (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          title="Share with users"
                          onClick={() => setShareTarget({ id: c.id, name: c.name })}
                        >
                          <Share2 className="size-4" />
                          <span className="sr-only">Share</span>
                        </Button>
                      ) : null}
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="size-8"
                        disabled={c.access_role === 'viewer'}
                        title={c.access_role === 'viewer' ? 'Viewers cannot edit' : undefined}
                        onClick={() => openEditModal(c.id)}
                      >
                        <Pencil className="size-4" />
                        <span className="sr-only">Edit</span>
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="size-8 text-destructive hover:text-destructive"
                        disabled={busyId === c.id || c.access_role !== 'owner'}
                        title={c.access_role !== 'owner' ? 'Only the owner can delete' : undefined}
                        onClick={() => void onDelete(c)}
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
              No connections yet.{' '}
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
