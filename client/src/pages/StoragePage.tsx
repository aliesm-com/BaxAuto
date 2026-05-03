import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Pencil, Plus, Trash2 } from 'lucide-react'

import type { StorageDestinationDTO } from '@/api/storageDestinations'
import { deleteStorageDestination, listStorageDestinations } from '@/api/storageDestinations'
import { StorageFormModal } from '@/components/storage/StorageFormModal'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

function summary(row: StorageDestinationDTO): string {
  if (row.kind === 's3') {
    const ep = row.endpoint_url?.trim()
    return ep ? `${row.bucket} · ${ep}` : row.bucket || '—'
  }
  const port = row.port != null ? `:${row.port}` : ''
  const tail = row.remote_path ? `${row.host}${port} · ${row.remote_path}` : `${row.host}${port}`
  return tail || '—'
}

export function StoragePage() {
  const [rows, setRows] = useState<StorageDestinationDTO[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()

  const { modalOpen, destinationId } = useMemo(() => {
    const showNew = searchParams.get('new') === '1'
    const raw = searchParams.get('edit')
    const parsed = raw ? Number(raw) : NaN
    const editId = Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
    return {
      modalOpen: showNew || editId != null,
      destinationId: editId,
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
    listStorageDestinations()
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function onDelete(row: StorageDestinationDTO) {
    if (!window.confirm(`Delete storage “${row.name}”?`)) return
    setBusyId(row.id)
    setError(null)
    try {
      await deleteStorageDestination(row.id)
      refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="space-y-6 p-6 lg:p-8">
      <StorageFormModal
        open={modalOpen}
        onOpenChange={(open) => {
          if (!open) closeModal()
        }}
        destinationId={destinationId}
        onSaved={() => refresh()}
      />

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Storage</h1>
          <p className="text-sm text-muted-foreground">
            Remote destinations for uploads (S3-compatible, SFTP, FTP). Wiring backups to these targets can follow in a later release.
          </p>
        </div>
        <Button type="button" className="rounded-full shadow-md" onClick={openCreateModal}>
          <Plus className="size-4" />
          Add destination
        </Button>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle>Destinations</CardTitle>
          <CardDescription>Each entry is private to your account. Secrets are encrypted when `DB_CREDENTIALS_FERNET_KEY` is set.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-3 pr-4 font-medium">Name</th>
                <th className="pb-3 pr-4 font-medium">Type</th>
                <th className="pb-3 pr-4 font-medium">Target</th>
                <th className="pb-3 font-medium w-32 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-border/60 last:border-0">
                  <td className="py-3 pr-4 font-medium">{r.name}</td>
                  <td className="py-3 pr-4">
                    <Badge variant="secondary" className="uppercase">
                      {r.kind}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">{summary(r)}</td>
                  <td className="py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button type="button" variant="ghost" size="icon" className="size-8" onClick={() => openEditModal(r.id)}>
                        <Pencil className="size-4" />
                        <span className="sr-only">Edit</span>
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="size-8 text-destructive hover:text-destructive"
                        disabled={busyId === r.id}
                        onClick={() => void onDelete(r)}
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
              No destinations yet.{' '}
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
