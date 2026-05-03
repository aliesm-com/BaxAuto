import { Bell, HelpCircle, Moon, Search, Sun } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/auth/AuthContext'
import { displayName, roleLabel } from '@/lib/roles'

export function AppTopBar() {
  const { user, logout, impersonator } = useAuth()
  const navigate = useNavigate()
  const [dark, setDark] = useState(false)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])

  const initials =
    user?.username
      .split(/[\s._-]+/)
      .map((s) => s[0])
      .join('')
      .slice(0, 2)
      .toUpperCase() ?? '?'

  return (
    <>
      {impersonator ? (
        <div className="flex shrink-0 items-center justify-center gap-3 border-b border-amber-500/30 bg-amber-500/15 px-4 py-2 text-xs text-amber-950 dark:text-amber-50">
          <span>
            Signed in as <strong className="font-semibold">@{user?.username}</strong>
            <span className="text-amber-900/80 dark:text-amber-100/80"> — acting superuser </span>
            <strong className="font-semibold">@{impersonator.username}</strong>
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 border-amber-700/40 bg-background/80 text-[11px]"
            onClick={() => {
              void logout().then(() => navigate('/login', { replace: true }))
            }}
          >
            Log out
          </Button>
        </div>
      ) : null}
      <header className="flex h-14 shrink-0 items-center gap-4 border-b border-border bg-card/80 px-6 backdrop-blur">
      <div className="relative mx-auto w-full max-w-xl flex-1">
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search backups, databases..."
          className="h-10 rounded-full border-border bg-muted/40 pl-10 pr-16"
        />
        <kbd className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground sm:inline-block">
          ⌘K
        </kbd>
      </div>
      <div className="flex items-center gap-1">
        <Button variant="ghost" size="icon" className="text-muted-foreground" type="button">
          <Bell className="size-5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="text-muted-foreground"
          type="button"
          onClick={() => setDark((d) => !d)}
        >
          {dark ? <Sun className="size-5" /> : <Moon className="size-5" />}
        </Button>
        <Button variant="ghost" size="icon" className="text-muted-foreground" type="button">
          <HelpCircle className="size-5" />
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="ml-2 gap-2 rounded-full px-2">
              <Avatar className="size-8 border border-border">
                <AvatarFallback className="bg-primary/15 text-xs font-semibold text-primary">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <div className="hidden text-left text-sm leading-tight md:block">
                <div className="font-medium">{user ? displayName(user) : '…'}</div>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Badge variant="secondary" className="h-5 px-1.5 text-[10px] font-normal">
                    {user ? roleLabel(user) : ''}
                  </Badge>
                </div>
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col gap-1">
                <span className="font-medium">{user ? displayName(user) : ''}</span>
                <span className="text-xs text-muted-foreground">@{user?.username}</span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to="/settings">Settings</Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => {
                void logout().then(() => navigate('/login', { replace: true }))
              }}
            >
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
    </>
  )
}
