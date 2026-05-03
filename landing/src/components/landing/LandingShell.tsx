import { useCallback, useEffect, useState } from 'react'

import { Github } from 'lucide-react'

import { SiteFooter } from '@/components/marketing/SiteFooter'
import { SiteHeader } from '@/components/marketing/SiteHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

import { DatabaseShowcase } from './DatabaseShowcase'
import { SplashScreen } from './SplashScreen'

export default function LandingShell() {
  const [splashVisible, setSplashVisible] = useState(true)
  const [splashExiting, setSplashExiting] = useState(false)

  const finishSplash = useCallback(() => {
    setSplashExiting(true)
    window.setTimeout(() => setSplashVisible(false), 850)
  }, [])

  useEffect(() => {
    if (splashVisible && !splashExiting) {
      document.body.style.overflow = 'hidden'
      return () => {
        document.body.style.overflow = ''
      }
    }
    document.body.style.overflow = ''
  }, [splashVisible, splashExiting])

  return (
    <>
      {splashVisible ? (
        <div
          className={cn('transition-opacity ease-out', splashExiting ? 'pointer-events-none opacity-0' : '')}
          style={{ transitionDuration: '850ms' }}
        >
          <SplashScreen onDone={finishSplash} />
        </div>
      ) : null}

      <div
        className={cn(
          'min-h-screen transition-opacity duration-700 ease-out',
          splashVisible && !splashExiting ? 'opacity-0' : 'opacity-100',
        )}
      >
        <SiteHeader active="home" />

        <main>
          <section className="relative overflow-hidden border-b border-border/50">
            <div className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(135deg,hsl(var(--brand-a)/0.12)_0%,transparent_42%,hsl(var(--brand-b)/0.1)_100%)] dark:bg-[linear-gradient(135deg,hsl(var(--brand-a)/0.16)_0%,transparent_45%,hsl(var(--brand-b)/0.14)_100%)]" />
            <div className="pointer-events-none absolute -left-32 top-20 size-[380px] rounded-full bg-brand-a/15 blur-3xl dark:bg-brand-a/25" />
            <div className="pointer-events-none absolute -right-24 bottom-0 size-[320px] rounded-full bg-brand-b/15 blur-3xl dark:bg-brand-b/22" />

            <div className="mx-auto max-w-3xl px-5 pb-20 pt-14 text-center lg:px-8 lg:pt-24">
              <Badge
                variant="secondary"
                className="mb-6 border-brand-a/30 bg-gradient-to-r from-brand-a/12 to-brand-b/12 px-4 py-1 font-normal text-foreground dark:from-brand-a/18 dark:to-brand-b/18"
              >
                Powered by AliESM
              </Badge>
              <h1 className="text-balance text-4xl font-bold tracking-tight text-foreground md:text-5xl lg:text-[3.25rem] lg:leading-[1.1]">
                Backup every datastore{' '}
                <span className="bg-gradient-to-r from-brand-a via-primary to-brand-b bg-clip-text text-transparent">
                  without the busywork
                </span>
              </h1>
              <p className="mx-auto mt-6 max-w-2xl text-pretty text-lg text-muted-foreground md:text-xl md:leading-relaxed">
                BaxAuto connects to PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch, and more — scheduled exports,
                guided restores, and observability you can ship with confidence. Run the OSS stack on your hardware{' '}
                <strong className="font-semibold text-foreground">or</strong> adopt{' '}
                <strong className="font-semibold text-foreground">BaxAuto Cloud</strong> when operations should disappear.
              </p>
              <div className="mt-11 flex flex-wrap justify-center gap-3">
                <Button
                  size="lg"
                  className="rounded-full bg-gradient-to-r from-brand-a to-brand-b px-9 text-white shadow-xl shadow-brand-a/20 hover:opacity-95 dark:shadow-brand-b/25"
                  asChild
                >
                  <a href="https://github.com" target="_blank" rel="noreferrer">
                    View open source
                  </a>
                </Button>
                <Button size="lg" variant="outline" className="rounded-full border-border/90 px-9 shadow-sm backdrop-blur-sm" asChild>
                  <a href="/pricing">See pricing</a>
                </Button>
                <Button size="lg" variant="outline" className="rounded-full border-border/90 px-9 shadow-sm backdrop-blur-sm" asChild>
                  <a href="#cloud">Explore Cloud</a>
                </Button>
              </div>

              <dl className="mx-auto mt-16 grid max-w-3xl grid-cols-2 gap-6 text-left sm:grid-cols-4">
                {[
                  { k: 'Engines', v: '8+ targets', d: 'Relational, document, cache, search' },
                  { k: 'Scheduling', v: 'Cron-grade', d: 'Retries & calendars baked in' },
                  { k: 'Artifacts', v: 'Encrypted-ready', d: 'Compress, encrypt, rotate' },
                  { k: 'Teams', v: 'RBAC-ready', d: 'Viewer/editor semantics' },
                ].map((row) => (
                  <div key={row.k} className="rounded-2xl border border-border/70 bg-card/60 px-4 py-4 backdrop-blur-sm">
                    <dt className="text-xs font-medium uppercase tracking-wider text-brand-b">{row.k}</dt>
                    <dd className="mt-1 text-lg font-semibold text-foreground">{row.v}</dd>
                    <dd className="mt-1 text-xs leading-snug text-muted-foreground">{row.d}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </section>

          <section id="features" className="mx-auto max-w-6xl px-5 py-20 lg:px-8">
            <div className="mb-14 text-center">
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
                Operator-grade{' '}
                <span className="bg-gradient-to-r from-brand-a to-brand-b bg-clip-text text-transparent">control plane</span>
              </h2>
              <p className="mx-auto mt-4 max-w-2xl text-muted-foreground md:text-lg">
                Automations stay boring when failures are loud — BaxAuto focuses on predictable pipelines, transparent logs,
                and restores that match real incidents.
              </p>
            </div>
            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {[
                {
                  title: 'Connector-aware workflows',
                  body: 'Engine-specific defaults keep dumps idiomatic while letting experts tune knobs per cluster.',
                },
                {
                  title: 'Lifecycle hygiene',
                  body: 'Retention ladders, checksum hints, and storage hints reduce orphaned blobs across buckets.',
                },
                {
                  title: 'Restore rehearsals',
                  body: 'Dry-run restores and sampling hooks mean fewer surprises when traffic returns.',
                },
                {
                  title: 'Scheduling intelligence',
                  body: 'Spread noisy jobs, quiet replicas first, and respect blackout windows without spreadsheets.',
                },
                {
                  title: 'Audit-friendly trails',
                  body: 'Who kicked off what, from where, with artifact fingerprints attached for compliance chats.',
                },
                {
                  title: 'Notification mesh',
                  body: 'Slack, email, and webhook outputs share the same templates — tweak once, reuse everywhere.',
                },
              ].map((card) => (
                <Card
                  key={card.title}
                  className="border-border/80 bg-card/75 backdrop-blur-sm transition-colors hover:border-brand-a/35 dark:hover:border-brand-b/40"
                >
                  <CardHeader>
                    <CardTitle className="text-lg">{card.title}</CardTitle>
                    <CardDescription className="text-base leading-relaxed">{card.body}</CardDescription>
                  </CardHeader>
                </Card>
              ))}
            </div>
          </section>

          <DatabaseShowcase />

          <section id="compare" className="mx-auto max-w-6xl px-5 py-20 lg:px-8">
            <h2 className="mb-6 text-center text-3xl font-bold tracking-tight md:text-4xl">
              Choose your{' '}
              <span className="bg-gradient-to-r from-brand-a to-brand-b bg-clip-text text-transparent">deployment lane</span>
            </h2>
            <p className="mx-auto mb-12 max-w-2xl text-center text-muted-foreground md:text-lg">
              Same philosophy: automate backups like any other production workflow — measurable, reversible, and boring at 3am.
            </p>
            <div className="grid gap-6 lg:grid-cols-2">
              <Card className="border-border/80 bg-card/80 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle>Open source</CardTitle>
                  <CardDescription className="text-base">
                    Host BaxAuto beside your databases. Fork the Django + React stack, wire your secrets manager, and stay
                    portable across clouds.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3 text-sm text-muted-foreground">
                    {[
                      'Docker-compose & bare-metal recipes',
                      'Bring-your-own object storage',
                      'Community roadmap influence via GitHub',
                      'No outbound telemetry by default',
                    ].map((item) => (
                      <li key={item} className="flex gap-2">
                        <span className="mt-2 size-1.5 shrink-0 rounded-full bg-brand-a" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                  <Button variant="outline" className="mt-8 w-full rounded-full" asChild>
                    <a href="https://github.com" target="_blank" rel="noreferrer">
                      <Github />
                      Browse repository
                    </a>
                  </Button>
                </CardContent>
              </Card>

              <Card
                id="cloud"
                className="relative overflow-hidden border-brand-b/35 bg-gradient-to-br from-card via-card to-brand-b/[0.06] shadow-[0_0_0_1px_hsl(var(--brand-b)/0.18)] backdrop-blur-sm dark:to-brand-b/[0.12]"
              >
                <div className="pointer-events-none absolute -right-16 top-10 size-56 rounded-full bg-brand-b/20 blur-3xl" />
                <CardHeader className="relative">
                  <CardTitle>BaxAuto Cloud</CardTitle>
                  <CardDescription className="text-base">
                    Managed upgrades, hardened networking primitives, and optional SOC-ready paperwork — same APIs you already
                    scripted against locally.
                  </CardDescription>
                </CardHeader>
                <CardContent className="relative">
                  <ul className="space-y-3 text-sm text-muted-foreground">
                    {[
                      'Hosted control plane & tenancy isolation',
                      'Patch orchestration without downtime roulette',
                      'Usage-aware billing with transparent meters',
                      'Waitlist today — capacity opens in phases',
                    ].map((item) => (
                      <li key={item} className="flex gap-2">
                        <span className="mt-2 size-1.5 shrink-0 rounded-full bg-brand-b" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                  <Button className="mt-8 w-full rounded-full bg-gradient-to-r from-brand-a to-brand-b text-white hover:opacity-95" asChild>
                    <a href="/pricing">Review pricing & waitlist</a>
                  </Button>
                </CardContent>
              </Card>
            </div>
          </section>

          <section className="mx-auto max-w-5xl px-5 py-16 lg:px-8">
            <Card className="overflow-hidden border-brand-a/25 bg-gradient-to-br from-brand-a/[0.06] via-card to-brand-b/[0.08] dark:from-brand-a/[0.1] dark:to-brand-b/[0.14]">
              <CardContent className="p-8 md:p-10">
                <p className="text-center text-lg leading-relaxed text-foreground md:text-xl">
                  BaxAuto is authored and shepherded by <strong>AliESM</strong> — opinionated tooling that respects operators,
                  measurable reliability, and sustainable maintenance over hype cycles.
                </p>
              </CardContent>
            </Card>
          </section>
        </main>

        <SiteFooter />
      </div>
    </>
  )
}
