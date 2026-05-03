export function SiteFooter() {
  return (
    <footer className="relative border-t border-border/70 px-5 py-14 text-center lg:px-8">
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-brand-b/35 to-transparent dark:via-brand-b/45" />
      <div className="text-muted-foreground">
        <span className="bg-gradient-to-r from-brand-a to-brand-b bg-clip-text font-mono font-semibold text-transparent">
          BaxAuto
        </span>
        <span className="mx-2 opacity-50">·</span>
        <span>
          Built by <strong className="text-foreground">AliESM</strong>
        </span>
      </div>
      <p className="mx-auto mt-4 max-w-xl text-xs leading-relaxed text-muted-foreground/85">
        Open-source and Cloud releases may ship on different schedules. See the repository for licensing.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-6 text-xs text-muted-foreground">
        <a href="/" className="transition-colors hover:text-foreground">
          Home
        </a>
        <a href="/pricing" className="transition-colors hover:text-foreground">
          Pricing
        </a>
        <a href="https://github.com" target="_blank" rel="noreferrer" className="transition-colors hover:text-foreground">
          GitHub
        </a>
      </div>
    </footer>
  )
}
