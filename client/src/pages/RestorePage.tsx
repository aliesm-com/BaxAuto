import { type FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { HardDrive } from 'lucide-react'

import type { BackupRecord } from '@/api/resources'
import { listBackupRecords } from '@/api/resources'
import { triggerRestore } from '@/api/restoresApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function RestorePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [backups, setBackups] = useState<BackupRecord[]>([])
  const [error, setError] = useState<string | null>(null)
  const [backupId, setBackupId] = useState<number | ''>('')
  const [filterText, setFilterText] = useState('')
  const [connectionFilter, setConnectionFilter] = useState<number | ''>('')
  const [engineFilter, setEngineFilter] = useState('')
  const [triggerFilter, setTriggerFilter] = useState('')
  const [flushBefore, setFlushBefore] = useState(false)
  const [applySchema, setApplySchema] = useState(false)
  const [truncateFirst, setTruncateFirst] = useState(false)
  const [drop, setDrop] = useState(false)
  const [running, setRunning] = useState(false)
  const [resultMsg, setResultMsg] = useState<string | null>(null)

  useEffect(() => {
    listBackupRecords()
      .then(setBackups)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load backups'))
  }, [])

  useEffect(() => {
    const raw = searchParams.get('backup')
    if (!raw) return
    const id = Number(raw)
    if (!Number.isInteger(id) || id < 1) return
    setBackupId(id)
  }, [searchParams])

  const successBackups = useMemo(() => backups.filter((b) => b.status === 'success'), [backups])

  const connectionOptions = useMemo(() => {
    const m = new Map<number, string>()
    for (const b of successBackups) {
      m.set(b.connection, b.connection_name)
    }
    return [...m.entries()].sort((a, b) => a[1].localeCompare(b[1]))
  }, [successBackups])

  const engineOptions = useMemo(
    () => [...new Set(successBackups.map((b) => b.engine))].sort((a, b) => a.localeCompare(b)),
    [successBackups],
  )

  const filteredSuccess = useMemo(() => {
    const q = filterText.trim().toLowerCase()
    return successBackups.filter((b) => {
      if (connectionFilter !== '' && b.connection !== connectionFilter) return false
      if (engineFilter && b.engine !== engineFilter) return false
      if (triggerFilter && b.trigger !== triggerFilter) return false
      if (!q) return true
      const hay = `${b.id} ${b.connection_name} ${b.engine} ${b.trigger} ${b.finished_at ?? ''} ${b.created_at}`.toLowerCase()
      return hay.includes(q)
    })
  }, [successBackups, filterText, connectionFilter, engineFilter, triggerFilter])

  const selectOptions = useMemo(() => {
    const inFiltered = new Set(filteredSuccess.map((b) => b.id))
    const selected = backupId !== '' ? successBackups.find((b) => b.id === backupId) : undefined
    const merged =
      selected && !inFiltered.has(selected.id) ? [selected, ...filteredSuccess] : [...filteredSuccess]
    const seen = new Set<number>()
    const dedup = merged.filter((b) => {
      if (seen.has(b.id)) return false
      seen.add(b.id)
      return true
    })
    return dedup.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  }, [filteredSuccess, successBackups, backupId])

  const selectedBackupValid = backupId !== '' && successBackups.some((b) => b.id === backupId)

  function setBackupAndUrl(id: number | '') {
    setBackupId(id)
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (id === '') next.delete('backup')
        else next.set('backup', String(id))
        return next
      },
      { replace: true },
    )
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setResultMsg(null)
    if (backupId === '') {
      setResultMsg('Choose a successful backup.')
      return
    }
    setRunning(true)
    try {
      const rr = await triggerRestore(backupId, {
        flush_before_restore: flushBefore || undefined,
        apply_schema: applySchema || undefined,
        truncate_first: truncateFirst || undefined,
        drop: drop || undefined,
      })
      setResultMsg(`Restore started (record #${rr.id}, status: ${rr.status}). Check Activity Logs for progress.`)
    } catch (err) {
      setResultMsg(err instanceof Error ? err.message : 'Restore failed')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6 lg:p-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Restore</h1>
        <p className="text-sm text-muted-foreground">
          Run a restore from a completed backup. Use filters when you have many rows; deep links use{' '}
          <code className="text-xs">?backup=id</code>.
        </p>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle>Run restore</CardTitle>
          <CardDescription>Only successful backups appear in the picker. Filters narrow the list below.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-6">
            {resultMsg ? (
              <p className={`text-sm ${resultMsg.toLowerCase().includes('restore failed') ? 'text-red-600' : 'text-muted-foreground'}`}>
                {resultMsg}
              </p>
            ) : null}
            <p className="text-xs text-muted-foreground">
              Track progress under{' '}
              <Link to="/logs" className="font-medium text-primary hover:underline">
                Activity Logs
              </Link>
              .
            </p>

            <div className="space-y-4 rounded-lg border border-border bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Filters</p>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="restore-search">Search</Label>
                  <Input
                    id="restore-search"
                    placeholder="ID, connection name, engine, date…"
                    value={filterText}
                    onChange={(e) => setFilterText(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="restore-conn">Connection</Label>
                  <select
                    id="restore-conn"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={connectionFilter === '' ? '' : String(connectionFilter)}
                    onChange={(e) => setConnectionFilter(e.target.value === '' ? '' : Number(e.target.value))}
                  >
                    <option value="">All connections</option>
                    {connectionOptions.map(([id, name]) => (
                      <option key={id} value={id}>
                        {name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="restore-engine">Engine</Label>
                  <select
                    id="restore-engine"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={engineFilter}
                    onChange={(e) => setEngineFilter(e.target.value)}
                  >
                    <option value="">All engines</option>
                    {engineOptions.map((en) => (
                      <option key={en} value={en}>
                        {en}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="restore-trigger">Trigger</Label>
                  <select
                    id="restore-trigger"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={triggerFilter}
                    onChange={(e) => setTriggerFilter(e.target.value)}
                  >
                    <option value="">All triggers</option>
                    <option value="manual">manual</option>
                    <option value="scheduled">scheduled</option>
                  </select>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Showing <span className="font-medium text-foreground">{filteredSuccess.length}</span> of{' '}
                <span className="font-medium text-foreground">{successBackups.length}</span> successful backups
                {backupId !== '' && !filteredSuccess.some((b) => b.id === backupId) ? (
                  <span className="text-amber-700 dark:text-amber-400"> · Current selection is outside filters (still valid).</span>
                ) : null}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="restore-backup">Backup</Label>
              <select
                id="restore-backup"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={backupId === '' ? '' : String(backupId)}
                onChange={(e) => setBackupAndUrl(e.target.value === '' ? '' : Number(e.target.value))}
              >
                <option value="">Select backup…</option>
                {selectOptions.map((b) => (
                  <option key={b.id} value={b.id}>
                    #{b.id} · {b.connection_name} · {b.engine} · {b.finished_at ?? b.created_at}
                  </option>
                ))}
              </select>
              {successBackups.length === 0 && !error ? (
                <p className="text-xs text-muted-foreground">
                  No successful backups yet.{' '}
                  <Link to="/databases" className="text-primary hover:underline">
                    Run one from Databases
                  </Link>
                  .
                </p>
              ) : null}
            </div>

            <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-4">
              <p className="text-xs font-medium text-muted-foreground">Driver options (optional)</p>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={flushBefore} onChange={(e) => setFlushBefore(e.target.checked)} className="size-4 rounded" />
                flush_before_restore
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={applySchema} onChange={(e) => setApplySchema(e.target.checked)} className="size-4 rounded" />
                apply_schema
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={truncateFirst} onChange={(e) => setTruncateFirst(e.target.checked)} className="size-4 rounded" />
                truncate_first
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={drop} onChange={(e) => setDrop(e.target.checked)} className="size-4 rounded" />
                drop (destructive)
              </label>
            </div>

            <Button type="submit" disabled={running || !selectedBackupValid}>
              <HardDrive className="mr-2 size-4" />
              {running ? 'Starting…' : 'Start restore'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Preview (filtered, newest first)</CardTitle>
          <CardDescription>
            Up to 15 rows matching filters —{' '}
            <Link to="/backups" className="text-primary hover:underline">
              full list on Backups
            </Link>
            .
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {filteredSuccess.slice(0, 15).map((b) => (
            <div key={b.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 py-2 last:border-0">
              <button
                type="button"
                className={`text-left font-medium hover:text-primary hover:underline ${backupId === b.id ? 'text-primary' : ''}`}
                onClick={() => setBackupAndUrl(b.id)}
              >
                #{b.id}
              </button>
              <span className="text-muted-foreground">{b.connection_name}</span>
              <Badge variant="outline" className="capitalize">
                {b.engine}
              </Badge>
              <Badge variant="secondary" className="text-[10px]">
                {b.trigger}
              </Badge>
            </div>
          ))}
          {filteredSuccess.length === 0 ? <p className="text-muted-foreground">No backups match these filters.</p> : null}
        </CardContent>
      </Card>
    </div>
  )
}
