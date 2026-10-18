import type { Metadata } from 'next'
import Image from 'next/image'
import Link from 'next/link'
import { ArrowRight, BookOpenCheck, Globe2, Network, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RDPSectionHeading } from '@/components/rdp/rdp-ui'
import { publishedCatalogues } from '@/lib/rdp-public-server'
import { catalogueDuration, catalogueTitle, cohortLink } from '@/lib/rdp-catalogue'

export const metadata: Metadata = {
  title: 'Ungozu R & D — Researcher Development Programmes',
  description: 'Practical research mentoring, training, and development programmes for early-career researchers.',
}

const pillars = [
  ['Research identity', 'Clarify your research direction, strengths, gaps and professional goals.', Sparkles],
  ['Research capability', 'Build skills in methods, writing, peer review and reproducibility.', BookOpenCheck],
  ['Career development', 'Strengthen collaboration, publishing, funding and professional networks.', Network],
  ['Research impact', 'Connect research to implementation, policy, innovation and public value.', Globe2],
] as const

export default async function RDPHomePage() {
  const catalogues = await publishedCatalogues()
  return <>
    <section className="border-b border-border/50 bg-gradient-to-b from-primary/5 to-background">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[1.25fr_.75fr] lg:px-8 lg:py-24">
        <div className="self-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Ungozu R & D</p>
          <h1 className="mt-4 max-w-4xl text-4xl font-semibold tracking-tight sm:text-5xl">Developing researchers who move from <span className="text-primary">questions to impact.</span></h1>
          <p className="mt-6 text-lg leading-7 text-muted-foreground">Flexible researcher-development programmes with practical learning, mentoring and a supportive research community.</p>
          <div className="mt-8 flex flex-wrap gap-3"><Button asChild size="lg"><Link href="#published-programmes">Explore available cohorts <ArrowRight className="ml-2 h-4 w-4"/></Link></Button><Button asChild size="lg" variant="outline"><Link href="/programme">View curriculum</Link></Button></div>
        </div>
        <div className="flex items-center justify-center"><div className="w-full max-w-sm rounded-2xl border bg-card p-8 shadow-sm"><Image src="/rdp-logo.png" alt="Ungozu R & D" width={700} height={700} priority className="h-auto w-full"/></div></div>
      </div>
    </section>
    <section id="published-programmes" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <RDPSectionHeading eyebrow="Available programmes" title="Explore programmes and cohorts" text="Explore mentoring options, learning activities, programme dates and fees for each available cohort."/>
      {catalogues.length ? <div className="mt-8 grid gap-5 md:grid-cols-2">{catalogues.map(c => <Card key={c.cohort.id}>
        <CardHeader><p className="text-xs uppercase tracking-wide text-primary">{c.cohort.label}</p><CardTitle>{catalogueTitle(c)}</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm"><p className="text-muted-foreground">{c.version?.overview || c.programme?.description || c.cohort.public_summary || 'Programme details are available on the curriculum page.'}</p><p><b>Duration:</b> {catalogueDuration(c)}</p><p><b>Dates:</b> {c.cohort.start_date} to {c.cohort.end_date}</p><p><b>Capacity:</b> {c.cohort.capacity} places</p><p><b>Applications:</b> {c.accepting_applications ? `Open until ${c.cohort.application_deadline}` : 'Not currently open'}</p>
        <div className="flex flex-wrap gap-2"><Button asChild variant="outline"><Link href={cohortLink('/programme', c.cohort.slug)}>View curriculum</Link></Button><Button asChild variant="outline"><Link href={cohortLink('/fees', c.cohort.slug)}>Packages & fees</Link></Button>{c.accepting_applications && <Button asChild><Link href={cohortLink('/apply', c.cohort.slug)}>Apply</Link></Button>}</div></CardContent></Card>)}</div> : <p className="mt-8 rounded-lg border p-6 text-sm text-muted-foreground">No published cohorts are currently available. Please check again when the next programme is announced.</p>}
    </section>
    <section className="border-y bg-muted/30"><div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8"><RDPSectionHeading eyebrow="Our approach" title="Research development beyond supervision"/><div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-4">{pillars.map(([title, description, Icon]) => <Card key={title}><CardHeader><Icon className="h-5 w-5 text-primary"/><CardTitle className="text-base">{title}</CardTitle></CardHeader><CardContent className="text-sm text-muted-foreground">{description}</CardContent></Card>)}</div></div></section>
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8"><RDPSectionHeading eyebrow="Development philosophy" title="Grow towards research independence" text="Participants develop practical research capability through reflection, structured tasks, individual guidance and professional networks."/><div className="mt-6"><Button asChild variant="outline"><Link href="/mentor">About the mentor</Link></Button></div></section>
  </>
}
