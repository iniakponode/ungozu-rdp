import type { Metadata } from 'next'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RDPSectionHeading } from '@/components/rdp/rdp-ui'

export const metadata: Metadata = { title: 'Programme | Ungozu R & D', description: 'The 12-month curriculum and mentoring model for the Ungozu R & D Researcher Development Programme.' }

const months = [
  ['1','Research identity & career direction','Baseline capability assessment, researcher identity, Individual Researcher Development Plan (IRDP), goals and mentoring constellation.'],
  ['2','Research problems & questions','Problem framing, research gaps, question quality, feasibility and resource-aware research design.'],
  ['3','Literature searching & synthesis','Search strategy, source evaluation, synthesis, reference management and literature-to-question alignment.'],
  ['4','Methods, ethics & reproducibility','Methodological fit, ethics, privacy, data-management planning and reproducible workflows.'],
  ['5','Data & digital research practice','Data organisation, analysis planning, documentation and appropriate low-cost/open tools.'],
  ['6','Academic writing & publishing','Manuscript architecture, journal selection, authorship, peer review and response-to-reviewers practice.'],
  ['7','Responsible AI for researchers','AI-assisted workflows, verification, disclosure, research integrity and human accountability.'],
  ['8','Collaboration, networking & sponsorship','Developmental networks, outreach, collaboration agreements, visibility and sponsorship.'],
  ['9','Grants & fellowships','Funding-call screening, concept notes, work plans, budgets and reviewer-oriented proposal development.'],
  ['10','Research communication & translation','Presentations, public communication, policy/industry translation and pathways to impact.'],
  ['11','Research leadership & mentoring others','Research-informed teaching, team habits, peer development and the mentor-multiplier model.'],
  ['12','Portfolio, continuation & graduation','Portfolio completion, development review, post-programme plan and graduation/closing event.'],
]

export default function ProgrammePage(){return <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
  <RDPSectionHeading eyebrow="12-month curriculum" title="A deliberate progression from research identity to research leadership" text="Each month combines a cohort masterclass, guided practice, accountability, independent work and mentor feedback. Quarterly development gates make progress visible."/>
  <div className="mt-10 grid gap-5 md:grid-cols-2">{months.map(([m,t,d])=><Card key={m}><CardHeader><div className="text-xs font-semibold uppercase tracking-widest text-primary">Month {m}</div><CardTitle className="text-lg">{t}</CardTitle></CardHeader><CardContent className="text-sm leading-6 text-muted-foreground">{d}</CardContent></Card>)}</div>
  <div className="mt-10 rounded-xl border border-border bg-muted/30 p-6"><h2 className="text-xl font-semibold">Quarterly development gates</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">Months 3, 6, 9 and 12 include formal progress reviews against the IRDP, outputs, research skills, network growth and next-quarter priorities. The final review culminates in the research portfolio and graduation on Saturday, 27 November 2027.</p></div>
  <div className="mt-8 flex gap-3"><Button asChild><Link href="/apply">Apply now</Link></Button><Button asChild variant="outline"><Link href="/fees">View fees</Link></Button></div>
</div>}
