import { Link } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  CalendarClock,
  Database,
  FolderOpen,
  HardDrive,
  LineChart as LineChartIcon,
  Plus,
  RefreshCw,
} from 'lucide-react'

import type { OverviewDTO } from '@/api/overview'
import { fetchOverview } from '@/api/overview'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'

function formatBytes(n: number | null): string {
  if (n == null || n <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let v = n
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v.toFixed(i > 1 ? 1 : 0)} ${units[i]}`
}

function timeAgo(iso: string): string {
  const d = new Date(iso).getTime()
  const s = Math.floor((Date.now() - d) / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 48) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export function OverviewPage() {
  const [data, setData] = useState<OverviewDTO | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const o = await fetchOverview()
        if (!cancelled) setData(o)
      } catch (e) {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : 'Failed to load')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const chartData = useMemo(
    () =>
      (data?.activity_week ?? []).map((d) => ({
        name: d.weekday,
        backups: d.success_count,
      })),
    [data],
  )

  const sparkData = useMemo(
    () =>
      (data?.sparkline ?? []).map((v, i) => ({
        i,
        v,
      })),
    [data],
  )

  const trendBadge = useMemo(() => {
    if (!data) return null
    if (data.trend_new) {
      return (
        <Badge variant="secondary" className="mt-2 font-normal">
          New this week
        </Badge>
      )
    }
    if (data.trend_percent === null || data.trend_percent === undefined) return null
    const up = data.trend_percent >= 0
    return (
      <Badge variant={up ? 'success' : 'destructive'} className="mt-2 font-normal">
        {up ? '+' : ''}
        {data.trend_percent}% vs prior week
      </Badge>
    )
  }, [data])

  if (loadError) {
    return (
      <div className="p-6 lg:p-8">
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          {loadError}
        </p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="p-6 lg:p-8">
        <p className="text-muted-foreground">Loading overview…</p>
      </div>
    )
  }

  const lastBackup = data.last_success
  const recent = data.recent_success
  const sch = data.health.scheduler
  const quotaLabel = `${formatBytes(data.storage.used_bytes)} / ${formatBytes(data.storage.quota_bytes)}`

  return (
    <div className="flex min-h-full gap-6 p-6 lg:p-8">
      <div className="min-w-0 flex-1 space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
            <p className="text-sm text-muted-foreground">
              Metrics from your backups and connections (server aggregate). Updated {timeAgo(data.generated_at)}.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" className="rounded-full">
              Last 7 days
            </Button>
            <Button asChild size="sm" className="rounded-full shadow-md">
              <Link to="/databases">
                <Plus className="size-4" />
                New Backup
              </Link>
            </Button>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Card className="overflow-hidden">
            <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Successful backups</CardTitle>
              <LineChartIcon className="size-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="flex items-end justify-between gap-2">
                <div>
                  <div className="text-3xl font-bold">{data.backups.success}</div>
                  {trendBadge}
                  <p className="mt-2 text-xs text-muted-foreground">
                    {data.backups.failed} failed · {data.backups.in_progress} in progress · {data.backups.total} total rows
                  </p>
                </div>
                <div className="h-12 w-24 text-primary">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={sparkData}>
                      <Line type="monotone" dataKey="v" stroke="hsl(262 83% 58%)" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Databases</CardTitle>
              <Database className="size-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{data.connections.count}</div>
              <p className="mt-2 text-xs text-muted-foreground">Saved connections</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Storage Used</CardTitle>
              <HardDrive className="size-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{formatBytes(data.storage.used_bytes)}</div>
              <Progress value={data.storage.quota_percent} className="mt-3 h-2" />
              <p className="mt-2 text-xs text-muted-foreground">
                {data.storage.quota_percent}% of plan ({quotaLabel})
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Last Backup</CardTitle>
              <RefreshCw className="size-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tabular-nums">{lastBackup ? timeAgo(lastBackup.created_at) : '—'}</div>
              {lastBackup ? (
                <Badge variant="success" className="mt-2 gap-1 font-normal">
                  Success
                </Badge>
              ) : (
                <p className="mt-2 text-xs text-muted-foreground">No backups yet</p>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 xl:grid-cols-5">
          <Card className="xl:col-span-3">
            <CardHeader>
              <CardTitle>Backup Activity</CardTitle>
              <CardDescription>Successful backups per day (last 7 days, server timezone)</CardDescription>
            </CardHeader>
            <CardContent className="pl-0">
              <div className="h-[280px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="fillBax" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="hsl(262 83% 58%)" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="hsl(262 83% 58%)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
                    <XAxis dataKey="name" tickLine={false} axisLine={false} className="text-xs" />
                    <YAxis allowDecimals={false} tickLine={false} axisLine={false} className="text-xs" width={32} />
                    <Tooltip
                      contentStyle={{
                        borderRadius: '8px',
                        border: '1px solid hsl(var(--border))',
                        background: 'hsl(var(--card))',
                      }}
                      labelFormatter={(l) => `${l}`}
                      formatter={(value: number) => [`${value} backups`, '']}
                    />
                    <Area type="monotone" dataKey="backups" stroke="hsl(262 83% 58%)" fill="url(#fillBax)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card className="xl:col-span-2">
            <CardHeader>
              <CardTitle>Recent Backups</CardTitle>
              <CardDescription>Latest successful runs</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {recent.length === 0 ? (
                <p className="text-sm text-muted-foreground">No backups yet. Run one from a database connection.</p>
              ) : (
                recent.map((b) => (
                  <div key={b.id} className="flex items-start justify-between gap-3 border-b border-border pb-3 last:border-0 last:pb-0">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{b.connection_name}</p>
                      <p className="text-xs capitalize text-muted-foreground">{b.engine}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {formatBytes(b.size_bytes)} · {timeAgo(b.created_at)}
                      </p>
                    </div>
                    <Badge variant="success" className="shrink-0">
                      Success
                    </Badge>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <aside className="hidden w-72 shrink-0 flex-col gap-6 xl:flex">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <Button variant="outline" className="justify-start gap-2" asChild>
              <Link to="/databases?new=1">
                <Database className="size-4" /> Add Database
              </Link>
            </Button>
            <Button variant="outline" className="justify-start gap-2" asChild>
              <Link to="/schedules?new=1">
                <CalendarClock className="size-4" /> Create Schedule
              </Link>
            </Button>
            <Button variant="outline" className="justify-start gap-2" asChild>
              <Link to="/restore">
                <RefreshCw className="size-4" /> Restore Backup
              </Link>
            </Button>
            <Button variant="outline" className="justify-start gap-2" asChild>
              <Link to="/logs">
                <FolderOpen className="size-4" /> View Logs
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">System Health</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Scheduler</span>
              {!sch.visible ? (
                <span className="text-xs text-muted-foreground">Admin-only detail</span>
              ) : (
                <span className="flex flex-col items-end gap-1 text-right">
                  <span className="flex items-center gap-2 font-medium">
                    <span className="relative flex h-2 w-2">
                      <span
                        className={`relative inline-flex h-2 w-2 rounded-full ${
                          sch.status === 'issues' ? 'bg-amber-500' : 'bg-emerald-500'
                        }`}
                      />
                    </span>
                    {sch.status === 'issues' ? 'Check failures' : 'OK'}
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    {sch.enabled_jobs} enabled · {sch.failed_jobs} failed last run
                  </span>
                </span>
              )}
            </div>
            <Separator />
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Storage</span>
                <span className="font-medium tabular-nums">{quotaLabel}</span>
              </div>
              <Progress value={data.storage.quota_percent} className="h-2" />
            </div>
            <Separator />
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Workers</span>
              <span className="font-medium text-muted-foreground">
                {data.health.workers_configured != null ? `${data.health.workers_configured} reported` : 'Not configured'}
              </span>
            </div>
          </CardContent>
        </Card>
      </aside>
    </div>
  )
}
