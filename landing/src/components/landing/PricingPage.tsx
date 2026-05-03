import { Check } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { SiteFooter } from '@/components/marketing/SiteFooter'
import { SiteHeader } from '@/components/marketing/SiteHeader'
import { cn } from '@/lib/utils'

const tiers = [
  {
    name: 'Community',
    price: '$0',
    cadence: 'forever',
    description: 'Self-hosted BaxAuto from source or Docker on your own infrastructure.',
    highlights: ['Full UI & API', 'Bring your own storage', 'Community support', 'Fork-friendly license'],
    cta: 'View on GitHub',
    href: 'https://github.com',
    featured: false,
  },
  {
    name: 'Team',
    price: '$29',
    cadence: '/ seat / month',
    description: 'For squads that want billing-ready packaging and prioritised roadmap input.',
    highlights: ['Everything in Community', 'SSO-ready roadmap', 'Priority email channel', 'Quarterly reviews'],
    cta: 'Contact sales',
    href: 'mailto:sales@example.com',
    featured: true,
  },
  {
    name: 'Cloud',
    price: 'Custom',
    cadence: 'usage-based',
    description: 'Managed BaxAuto with SLA options — same core, less operational overhead.',
    highlights: ['Hosted control plane', 'Regional deployments', 'Encryption & audit helpers', 'Dedicated success'],
    cta: 'Join waitlist',
    href: 'https://github.com',
    featured: false,
  },
]

const faqs = [
  {
    q: 'Can I switch between self-hosted and Cloud later?',
    a: 'Yes. BaxAuto Cloud builds on the same APIs and workflows as the open-source stack so migrations stay predictable.',
  },
  {
    q: 'Do you charge per database connection?',
    a: 'Community is unlimited on your hardware. Team and Cloud pricing scales with seats and managed usage — final meters ship with GA.',
  },
  {
    q: 'Is there a trial for Team?',
    a: 'Pilot programs open on request. Mention your workload profile when you reach out.',
  },
]

export default function PricingPage() {
  return (
    <div className="min-h-screen">
      <SiteHeader active="pricing" />

      <main>
        <section className="relative overflow-hidden border-b border-border/60 px-5 pb-16 pt-14 lg:px-8 lg:pt-20">
          <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_90%_70%_at_50%_-10%,hsl(var(--brand-a)/0.14),transparent_58%),radial-gradient(ellipse_70%_50%_at_100%_40%,hsl(var(--brand-b)/0.12),transparent_52%)] dark:bg-[radial-gradient(ellipse_90%_70%_at_50%_-10%,hsl(var(--brand-a)/0.18),transparent_58%),radial-gradient(ellipse_70%_50%_at_100%_40%,hsl(var(--brand-b)/0.16),transparent_52%)]" />
          <div className="mx-auto max-w-3xl text-center">
            <Badge variant="secondary" className="mb-6 border-brand-b/25 bg-brand-b/10 text-brand-b dark:bg-brand-b/15">
              Pricing overview
            </Badge>
            <h1 className="text-balance text-4xl font-bold tracking-tight md:text-5xl">
              Transparent tiers for{' '}
              <span className="bg-gradient-to-r from-brand-a to-brand-b bg-clip-text text-transparent">builders & buyers</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-pretty text-lg text-muted-foreground">
              Start free with the open-source core. Scale into Team for organisational glue, or delegate ops to BaxAuto Cloud
              when you want SLAs and managed lifecycle.
            </p>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-5 py-16 lg:px-8 lg:py-24">
          <div className="grid gap-6 lg:grid-cols-3">
            {tiers.map((tier) => (
              <Card
                key={tier.name}
                className={cn(
                  'relative flex flex-col border-border/80 bg-card/85 backdrop-blur-sm',
                  tier.featured &&
                    'border-brand-a/35 shadow-xl shadow-brand-a/[0.08] ring-1 ring-brand-b/20 dark:border-brand-b/40 dark:shadow-brand-b/[0.12]',
                )}
              >
                {tier.featured ? (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-brand-a to-brand-b px-4 py-1 text-xs font-semibold text-white shadow-md">
                    Most flexible
                  </div>
                ) : null}
                <CardHeader className="pb-4 pt-8">
                  <CardTitle className="text-2xl">{tier.name}</CardTitle>
                  <CardDescription className="text-base">{tier.description}</CardDescription>
                  <div className="pt-4">
                    <span className="text-4xl font-bold tracking-tight">{tier.price}</span>
                    <span className="text-muted-foreground"> {tier.cadence}</span>
                  </div>
                </CardHeader>
                <CardContent className="flex-1 space-y-3 pt-0">
                  {tier.highlights.map((item) => (
                    <div key={item} className="flex gap-3 text-sm text-muted-foreground">
                      <Check className="mt-0.5 size-4 shrink-0 text-brand-a" aria-hidden />
                      <span>{item}</span>
                    </div>
                  ))}
                </CardContent>
                <CardFooter className="pb-8 pt-4">
                  <Button
                    variant="outline"
                    size="lg"
                    className={cn(
                      'w-full rounded-full',
                      tier.featured &&
                        'border-0 bg-gradient-to-r from-brand-a to-brand-b text-white shadow-lg hover:opacity-95 hover:text-white',
                    )}
                    asChild
                  >
                    <a href={tier.href} target={tier.href.startsWith('mailto:') ? undefined : '_blank'} rel="noreferrer">
                      {tier.cta}
                    </a>
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
          <p className="mx-auto mt-10 max-w-3xl text-center text-sm text-muted-foreground">
            Figures shown are directional placeholders until BaxAuto Cloud GA. Community Edition stays free and source-available.
          </p>
        </section>

        <section className="mx-auto max-w-4xl px-5 pb-24 lg:px-8">
          <h2 className="mb-10 text-center text-2xl font-bold tracking-tight md:text-3xl">Billing FAQs</h2>
          <div className="space-y-4">
            {faqs.map((item) => (
              <Card key={item.q} className="border-border/80 bg-card/70">
                <CardHeader>
                  <CardTitle className="text-lg">{item.q}</CardTitle>
                  <CardDescription className="text-base leading-relaxed text-muted-foreground">{item.a}</CardDescription>
                </CardHeader>
              </Card>
            ))}
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  )
}
