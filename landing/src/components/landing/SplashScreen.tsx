import { useEffect, useState } from 'react'

import { cn } from '@/lib/utils'

const FULL = 'Bax Auto'

export function SplashScreen({ onDone }: { onDone: () => void }) {
  const [typed, setTyped] = useState('')
  const [showPowered, setShowPowered] = useState(false)

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (reduced) {
      setTyped(FULL)
      setShowPowered(true)
      const t = window.setTimeout(onDone, 500)
      return () => window.clearTimeout(t)
    }

    let i = 0
    const step = () => {
      setTyped(FULL.slice(0, i))
      if (i < FULL.length) {
        i++
        window.setTimeout(step, 92)
      } else {
        setShowPowered(true)
        window.setTimeout(onDone, 1450)
      }
    }
    step()
  }, [onDone])

  return (
    <div
      className={cn(
        'fixed inset-0 z-[9999] flex items-center justify-center bg-background',
        'bg-[radial-gradient(ellipse_85%_65%_at_28%_38%,hsl(var(--brand-a)/0.26)_0%,transparent_55%),radial-gradient(ellipse_75%_55%_at_72%_62%,hsl(var(--brand-b)/0.22)_0%,transparent_52%)]',
        'transition-opacity ease-out dark:bg-[radial-gradient(ellipse_85%_65%_at_28%_38%,hsl(var(--brand-a)/0.32)_0%,transparent_55%),radial-gradient(ellipse_75%_55%_at_72%_62%,hsl(var(--brand-b)/0.26)_0%,transparent_52%)]',
      )}
      style={{ transitionDuration: '850ms' }}
      aria-live="polite"
      aria-label="Loading"
    >
      <div className="px-8 text-center">
        <div className="min-h-[1.2em] font-mono text-[clamp(1.75rem,6vw,3rem)] font-medium tracking-tight text-foreground">
          <span>{typed}</span>
          <span className="ml-0.5 inline-block h-[1.1em] w-[3px] translate-y-[0.05em] animate-caret-blink bg-gradient-to-b from-brand-a to-brand-b" />
        </div>
        <p
          className={cn(
            'mt-5 font-mono text-sm font-normal lowercase tracking-[0.08em] text-muted-foreground transition-all duration-500',
            showPowered ? 'translate-y-0 opacity-100' : 'translate-y-1.5 opacity-0',
          )}
        >
          Powered by AliESM
        </p>
      </div>
    </div>
  )
}
