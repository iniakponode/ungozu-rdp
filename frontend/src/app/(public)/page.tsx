import type { Metadata } from 'next'
import Image from 'next/image'
import Link from 'next/link'
import { ArrowRight, BookOpenCheck, CalendarDays, Globe2, Network, Sparkles, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RDPSectionHeading } from '@/components/rdp/rdp-ui'

export const metadata: Metadata = {
  title: 'Ungozu R & D Researcher Development Programme',
  description: 'A structured 12-month mentoring and researcher-development programme for early-career researchers, especially those navigating low-resource research environments.',
}

const pillars = [
  ['Research identity', 'Clarify your research direction, strengths, gaps, goals and the researcher you are becoming.', Sparkles],
  ['Research capability', 'Strengthen literature work, methods, data practice, reproducibility, writing and peer review.', BookOpenCheck],
  ['Career capital', 'Build publications, grants, fellowships, collaborations, visibility and a credible professional network.', Network],
  ['Research impact', 'Connect rigorous research to real problems, implementation, innovation, policy and public value.', Globe2],
] as const

export default function RDPHomePage() {
  return <>
    <section className="border-b border-border/50 bg-gradient-to-b from-primary/5 to-background">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[1.25fr_.75fr] lg:px-8 lg:py-24">
        <div className="self-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Founding Cohort 2026/2027</p>
          <h1 className="mt-4 max-w-4xl text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl">Developing researchers who can move from <span className="text-primary">questions to impact.</span></h1>
          <p className="mt-6 max-w-3xl text-base leading-7 text-muted-foreground sm:text-lg">A structured 12-month mentoring and researcher-development programme for early-career researchers, especially those navigating low-resource research environments.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild size="lg"><Link href="/apply">Apply for the Founding Cohort <ArrowRight className="ml-2 h-4 w-4"/></Link></Button>
            <Button asChild size="lg" variant="outline"><Link href="/programme">Explore the programme</Link></Button>
          </div>
          <div className="mt-8 grid max-w-3xl gap-3 text-sm sm:grid-cols-3">
            <div className="rounded-lg border border-border bg-card p-3"><Users className="mb-2 h-4 w-4 text-primary"/><b>10 researchers</b><p className="mt-1 text-xs text-muted-foreground">Small founding cohort</p></div>
            <div className="rounded-lg border border-border bg-card p-3"><CalendarDays className="mb-2 h-4 w-4 text-primary"/><b>Apply by 2 Nov 2026</b><p className="mt-1 text-xs text-muted-foreground">Applications open 2 Oct</p></div>
            <div className="rounded-lg border border-border bg-card p-3"><CalendarDays className="mb-2 h-4 w-4 text-primary"/><b>2 Dec 2026–2 Dec 2027</b><p className="mt-1 text-xs text-muted-foreground">Graduation: 27 Nov 2027</p></div>
          </div>
        </div>
        <div className="flex items-center justify-center">
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-8 shadow-sm">
            <Image src="/rdp-logo.png" alt="Ungozu R & D Researcher Development Programme" width={700} height={700} priority className="h-auto w-full"/>
          </div>
        </div>
      </div>
    </section>

    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <RDPSectionHeading eyebrow="Why this programme" title="Research development beyond supervision" text="The programme combines mentoring, practical research capability, publishing support, digital and responsible-AI practice, grant readiness, networking, sponsorship and research-to-impact thinking." />
      <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
        {pillars.map(([title, text, Icon], idx) => <Card key={title}><CardHeader><div className="flex items-center justify-between"><Icon className="h-5 w-5 text-primary"/><span className="text-xs font-semibold text-muted-foreground">0{idx+1}</span></div><CardTitle className="text-base">{title}</CardTitle></CardHeader><CardContent className="text-sm leading-6 text-muted-foreground">{text}</CardContent></Card>)}
      </div>
    </section>

    <section className="border-y border-border/50 bg-muted/30">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <RDPSectionHeading eyebrow="Programme at a glance" title="A full year of structured development" />
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[['12','Monthly development themes'],['48','Weekly learning cycles'],['4','Quarterly development gates'],['1','Year-end research portfolio']].map(([n,l])=><div key={l} className="rounded-xl border border-border bg-background p-6"><p className="text-4xl font-semibold text-primary">{n}</p><p className="mt-2 text-sm text-muted-foreground">{l}</p></div>)}
        </div>
      </div>
    </section>

    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <RDPSectionHeading eyebrow="Mentoring philosophy" title="You should leave more independent than you arrived." text="The model is structured near-peer development: recent research experience, practical academic guidance, accountability, sponsorship and deliberate connection to wider expertise when needed." />
      <blockquote className="mt-8 rounded-2xl border-l-4 border-primary bg-primary/5 p-6 text-lg leading-8">“I demonstrate → we do it together → you do it and I review → you do it independently → you help another researcher.”</blockquote>
      <div className="mt-8 flex flex-wrap gap-3"><Button asChild><Link href="/programme">See the 12-month journey</Link></Button><Button asChild variant="outline"><a href="https://iniakpothompson.com" target="_blank" rel="noreferrer">Meet Dr. Thompson</a></Button></div>
    </section>

    <section className="border-t border-border/50 bg-primary text-primary-foreground">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-12 sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
        <div><p className="text-xs font-semibold uppercase tracking-[0.2em] opacity-80">Founding cohort</p><h2 className="mt-2 text-2xl font-semibold">Applications are open for 10 researchers.</h2><p className="mt-2 text-sm opacity-80">Application period: 2 October–2 November 2026.</p></div>
        <Button asChild variant="secondary" size="lg"><Link href="/apply">Start your application <ArrowRight className="ml-2 h-4 w-4"/></Link></Button>
      </div>
    </section>
  </>
}
