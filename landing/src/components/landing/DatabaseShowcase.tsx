import { useCallback, useEffect, useState } from 'react'

import useEmblaCarousel from 'embla-carousel-react'
import { ChevronLeft, ChevronRight, Database } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

type Engine = {
  name: string
  kind: string
  description: string
  highlights: string[]
}

const ENGINES: Engine[] = [
  {
    name: 'PostgreSQL',
    kind: 'Relational',
    description: 'Logical dumps, compression-friendly archives, and workflow hooks for clusters.',
    highlights: ['Roles & extensions aware', 'Streaming-compatible layouts'],
  },
  {
    name: 'MySQL & MariaDB',
    kind: 'Relational',
    description: 'Consistent snapshots with mysqldump-compatible paths and scheduled rotations.',
    highlights: ['Replica-aware jobs', 'Defined retention windows'],
  },
  {
    name: 'MongoDB',
    kind: 'Document',
    description: 'mongodump-style bundles with namespace filters and oplog considerations.',
    highlights: ['Sharded-friendly exports', 'Point-in-time helpers'],
  },
  {
    name: 'Redis',
    kind: 'In-memory',
    description: 'RDB snapshots and AOF-aware strategies depending on your persistence mode.',
    highlights: ['Low-noise scheduling', 'Fast iteration cycles'],
  },
  {
    name: 'SQLite',
    kind: 'Embedded',
    description: 'File-backed backups with integrity checks for edge deployments.',
    highlights: ['Single-file artifacts', 'Ideal for agents & IoT'],
  },
  {
    name: 'Microsoft SQL Server',
    kind: 'Relational',
    description: 'Enterprise backups via compatible tooling and credential hygiene.',
    highlights: ['Encrypted transports', 'Operator-focused logs'],
  },
  {
    name: 'Elasticsearch',
    kind: 'Search',
    description: 'Snapshot repositories and index-aware exports for observability stacks.',
    highlights: ['Cluster snapshots', 'Restore rehearsals'],
  },
  {
    name: 'Cassandra',
    kind: 'Wide-column',
    description: 'Ring-aware backup windows with clear nodetool semantics.',
    highlights: ['Incremental-friendly flows', 'Multi-DC aware'],
  },
]

export function DatabaseShowcase() {
  const [emblaRef, emblaApi] = useEmblaCarousel({
    align: 'start',
    loop: true,
    skipSnaps: false,
    dragFree: false,
  })
  const [selected, setSelected] = useState(0)

  const scrollPrev = useCallback(() => emblaApi?.scrollPrev(), [emblaApi])
  const scrollNext = useCallback(() => emblaApi?.scrollNext(), [emblaApi])

  useEffect(() => {
    if (!emblaApi) return
    const onSelect = () => setSelected(emblaApi.selectedScrollSnap())
    emblaApi.on('select', onSelect)
    onSelect()
    return () => {
      emblaApi.off('select', onSelect)
    }
  }, [emblaApi])

  return (
    <section id="engines" className="relative mx-auto max-w-6xl px-5 py-20 lg:px-8">
      <div className="pointer-events-none absolute inset-x-4 top-0 -z-10 h-72 rounded-[2rem] bg-gradient-to-br from-brand-a/[0.07] via-transparent to-brand-b/[0.09] blur-2xl dark:from-brand-a/[0.12] dark:to-brand-b/[0.14]" />
      <div className="mb-12 text-center">
        <Badge variant="secondary" className="mb-4 border-brand-a/25 bg-brand-a/10 text-brand-a dark:border-brand-a/35 dark:bg-brand-a/15 dark:text-brand-a">
          Supported engines
        </Badge>
        <h2 className="text-balance text-3xl font-bold tracking-tight md:text-4xl">
          One workflow across{' '}
          <span className="bg-gradient-to-r from-brand-a to-brand-b bg-clip-text text-transparent">the stacks you run</span>
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-pretty text-muted-foreground md:text-lg">
          BaxAuto is built around real operator surfaces — relational, document, cache, search, and wide-column systems.
          Roadmaps evolve with the community; check GitHub for the latest connector matrix.
        </p>
      </div>

      <div className="relative">
        <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-14 bg-gradient-to-r from-background to-transparent md:w-24" />
        <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-14 bg-gradient-to-l from-background to-transparent md:w-24" />

        <div ref={emblaRef} className="overflow-hidden pb-2 md:-mx-2">
          <div className="flex touch-pan-y gap-4 md:gap-5">
            {ENGINES.map((engine) => (
              <div
                key={engine.name}
                className="min-w-0 shrink-0 basis-[min(100%,320px)] sm:basis-[340px] md:basis-[360px]"
              >
                <Card className="group h-full border-border/80 bg-card/90 shadow-lg shadow-brand-a/[0.04] backdrop-blur-sm transition-all duration-300 hover:border-brand-a/30 hover:shadow-xl hover:shadow-brand-b/[0.06] dark:bg-card/70 dark:shadow-brand-a/[0.06] dark:hover:border-brand-b/35">
                  <CardHeader className="space-y-3 pb-2">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex size-11 items-center justify-center rounded-xl bg-gradient-to-br from-brand-a/15 to-brand-b/15 text-brand-a ring-1 ring-brand-a/20 dark:from-brand-a/25 dark:to-brand-b/20 dark:text-brand-a">
                        <Database className="size-5" aria-hidden />
                      </div>
                      <Badge variant="outline" className="shrink-0 border-brand-b/25 font-normal text-brand-b/95 dark:border-brand-b/40">
                        {engine.kind}
                      </Badge>
                    </div>
                    <CardTitle className="text-xl tracking-tight">{engine.name}</CardTitle>
                    <CardDescription className="text-base leading-relaxed">{engine.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      {engine.highlights.map((line) => (
                        <li key={line} className="flex gap-2">
                          <span className="mt-2 size-1 shrink-0 rounded-full bg-gradient-to-br from-brand-a to-brand-b" />
                          <span>{line}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-8 flex flex-col items-center gap-5 sm:flex-row sm:justify-center">
          <div className="flex gap-2">
            <Button
              type="button"
              size="icon"
              variant="outline"
              className="rounded-full border-border/80 shadow-sm"
              onClick={scrollPrev}
              aria-label="Previous engines"
            >
              <ChevronLeft className="size-5" />
            </Button>
            <Button
              type="button"
              size="icon"
              variant="outline"
              className="rounded-full border-border/80 shadow-sm"
              onClick={scrollNext}
              aria-label="Next engines"
            >
              <ChevronRight className="size-5" />
            </Button>
          </div>
          <div className="flex gap-1.5" role="tablist" aria-label="Carousel pagination">
            {ENGINES.map((_, i) => (
              <button
                key={ENGINES[i].name}
                type="button"
                className={cn(
                  'h-2 rounded-full transition-all duration-300',
                  i === selected ? 'w-8 bg-gradient-to-r from-brand-a to-brand-b' : 'w-2 bg-muted-foreground/35 hover:bg-muted-foreground/55',
                )}
                aria-label={`Go to slide ${i + 1}`}
                aria-current={i === selected}
                onClick={() => emblaApi?.scrollTo(i)}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
