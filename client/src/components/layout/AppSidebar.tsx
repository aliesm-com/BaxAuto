import type { ComponentType } from 'react'
import {
  Activity,
  Boxes,
  CalendarClock,
  Database,
  HardDrive,
  LayoutDashboard,
  RotateCcw,
  Settings,
  ShieldAlert,
  Users,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

import { useAuth } from '@/auth/AuthContext'
import { canManageUsers, canMutate } from '@/auth/access'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import type { AuthUser } from '@/types/user'

type NavAccess = 'auth' | 'mutate' | 'admin' | 'soon'

interface NavDef {
  to: string
  label: string
  icon: ComponentType<{ className?: string }>
  access: NavAccess
  /** If true, omit this row when the user cannot satisfy ``access`` (only used with ``admin``). */
  hideWhenDenied?: boolean
}

const overviewItem: NavDef = { to: '/', label: 'Overview', icon: LayoutDashboard, access: 'auth' }

const mainNav: NavDef[] = [
  { to: '/backups', label: 'Backups', icon: HardDrive, access: 'auth' },
  { to: '/databases', label: 'Databases', icon: Database, access: 'auth' },
  { to: '/schedules', label: 'Schedules', icon: CalendarClock, access: 'auth' },
  { to: '/storage', label: 'Storage', icon: Boxes, access: 'auth' },
  { to: '/alerts', label: 'Alerts', icon: ShieldAlert, access: 'soon' },
]

const advancedNav: NavDef[] = [
  { to: '/logs', label: 'Activity Logs', icon: Activity, access: 'auth' },
  { to: '/restore', label: 'Restore', icon: RotateCcw, access: 'mutate' },
  { to: '/users', label: 'Users', icon: Users, access: 'admin', hideWhenDenied: true },
]

function navAllowed(user: AuthUser | null, access: NavAccess): boolean {
  if (!user) return false
  switch (access) {
    case 'auth':
      return true
    case 'mutate':
      return canMutate(user)
    case 'admin':
      return canManageUsers(user)
    case 'soon':
      return false
    default:
      return false
  }
}

function NavRow({
  to,
  label,
  icon: Icon,
  locked,
  reason,
}: {
  to: string
  label: string
  icon: ComponentType<{ className?: string }>
  locked: boolean
  reason?: string
}) {
  if (locked) {
    return (
      <span
        title={reason}
        className={cn(
          'flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground opacity-55',
        )}
      >
        <Icon className="size-4 shrink-0 opacity-80" />
        {label}
      </span>
    )
  }
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'bg-accent text-primary shadow-sm'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground',
        )
      }
    >
      <Icon className="size-4 shrink-0 opacity-80" />
      {label}
    </NavLink>
  )
}

export function AppSidebar() {
  const { user } = useAuth()

  function renderDef(def: NavDef) {
    const allowed = navAllowed(user, def.access)
    if (def.hideWhenDenied && !allowed) return null
    const locked = !allowed
    const reason =
      def.access === 'soon'
        ? 'Coming soon'
        : def.access === 'mutate'
          ? 'Read-only account — restore is disabled.'
          : def.access === 'admin'
            ? 'Requires app admin.'
            : undefined
    return <NavRow key={def.to} to={def.to} label={def.label} icon={def.icon} locked={locked} reason={reason} />
  }

  return (
    <aside className="flex h-full w-60 flex-col border-r border-border bg-card">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10">
          <Boxes className="size-5 text-primary" />
        </div>
        <span className="text-lg font-semibold tracking-tight">BaxAuto</span>
      </div>
      <ScrollArea className="flex-1 px-3 py-4">
        <nav className="flex flex-col gap-1">{renderDef(overviewItem)}</nav>
        <p className="mb-2 mt-6 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Main</p>
        <nav className="flex flex-col gap-1">{mainNav.map(renderDef)}</nav>
        <p className="mb-2 mt-6 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Advanced</p>
        <nav className="flex flex-col gap-1">{advancedNav.map(renderDef)}</nav>
      </ScrollArea>
      <Separator />
      <div className="p-3">
        <NavRow to="/settings" label="Settings" icon={Settings} locked={false} />
      </div>
    </aside>
  )
}
