import { Github } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

import { ThemeToggle } from './ThemeToggle'

export type SiteHeaderProps = {
  active?: 'home' | 'pricing'
}

export function SiteHeader({ active = 'home' }: SiteHeaderProps) {
  const link = 'text-sm font-medium text-muted-foreground transition-colors hover:text-foreground'
  const activeLink = 'text-foreground'

  return (
    <header className="sticky top-0 z-50 border-b border-border/70 bg-background/80 backdrop-blur-xl">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-brand-a/40 to-transparent dark:via-brand-a/50" />
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3.5 lg:px-8">
        <a href="/" className="group flex items-center gap-2 font-mono text-lg font-semibold tracking-tight">
          <span className="bg-gradient-to-r from-brand-a to-brand-b bg-clip-text text-transparent transition-opacity group-hover:opacity-90">
            BaxAuto
          </span>
        </a>
        <nav className="flex flex-wrap items-center justify-end gap-4 sm:gap-6">
          <a href="/#features" className={cn(link, active === 'home' ? '' : '')}>
            Features
          </a>
          <a href="/#engines" className={cn(link, active === 'home' ? '' : '')}>
            Engines
          </a>
          <a href="/#compare" className={link}>
            Open source & Cloud
          </a>
          <a href="/pricing" className={cn(link, active === 'pricing' ? activeLink : '')}>
            Pricing
          </a>
          <ThemeToggle />
          <Button variant="outline" size="sm" className="rounded-full border-border/80 shadow-sm" asChild>
            <a href="https://github.com" target="_blank" rel="noreferrer">
              <Github />
              GitHub
            </a>
          </Button>
        </nav>
      </div>
    </header>
  )
}
