import type { Metadata } from 'next'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RDPSectionHeading } from '@/components/rdp/rdp-ui'
import { publishedCatalogues } from '@/lib/rdp-public-server'
import { chooseCatalogue, catalogueTitle, catalogueDuration, cohortLink } from '@/lib/rdp-catalogue'

export const metadata: Metadata = { title: 'Published programmes | Ungozu R & D', description: 'Explore the currently published programmes, curricula and cohorts.' }

export default async function ProgrammePage({searchParams}:{searchParams:Promise<{cohort?:string}>}) {
 const selected = (await searchParams).cohort
 const catalogues = await publishedCatalogues()
 const c = chooseCatalogue(catalogues, selected)
 return <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
  <RDPSectionHeading eyebrow="Programme catalogue" title={c ? catalogueTitle(c) : 'Published researcher-development programmes'} text={c?.version?.overview || c?.programme?.description || 'Explore available mentoring programmes, learning outcomes, activities and support options.'}/>
  {catalogues.length > 1 && <nav aria-label="Choose cohort" className="mt-6 flex flex-wrap gap-2">{catalogues.map(x => <Button asChild key={x.cohort.id} variant={x.cohort.id===c?.cohort.id?'default':'outline'} size="sm"><Link href={cohortLink('/programme', x.cohort.slug)}>{x.cohort.label}</Link></Button>)}</nav>}
  {!c ? <p className="mt-8 rounded-lg border p-6 text-sm text-muted-foreground">No published programme is currently available.</p> : <>
    <div className="mt-8 rounded-xl border bg-muted/30 p-5 text-sm"><p><b>Cohort:</b> {c.cohort.label}</p><p><b>Duration:</b> {catalogueDuration(c)}</p><p><b>Dates:</b> {c.cohort.start_date} – {c.cohort.end_date}</p>{c.version?.learning_outcomes && <p className="mt-2 whitespace-pre-wrap"><b>Learning outcomes:</b> {c.version.learning_outcomes}</p>}</div>
    <h2 className="mt-10 text-xl font-semibold">Curriculum modules</h2>
    {c.modules.length ? <div className="mt-5 grid gap-5 md:grid-cols-2">{c.modules.map(m => <Card key={m.id}><CardHeader><p className="text-xs font-semibold uppercase tracking-wide text-primary">Module {m.sequence_number}</p><CardTitle>{m.title}</CardTitle></CardHeader><CardContent className="space-y-3 text-sm text-muted-foreground">{m.summary&&<p>{m.summary}</p>}{m.learning_outcomes&&<p className="whitespace-pre-wrap">{m.learning_outcomes}</p>}{m.items.length > 0 && <ul className="list-disc space-y-1 pl-5">{m.items.map(i => <li key={i.id}>{i.title}{i.description?` — ${i.description}`:''}</li>)}</ul>}</CardContent></Card>)}</div> : <p className="mt-4 text-sm text-muted-foreground">Learning modules for this programme are not available at present.</p>}
    {c.packages.length > 0 && <><h2 className="mt-10 text-xl font-semibold">Participation packages</h2><div className="mt-5 grid gap-5 md:grid-cols-2">{c.packages.map(p => <Card key={p.id}><CardHeader><CardTitle>{p.name}</CardTitle></CardHeader><CardContent className="text-sm text-muted-foreground">{p.description&&<p>{p.description}</p>}{p.entitlements.length > 0 && <ul className="mt-3 list-disc space-y-1 pl-5">{p.entitlements.map(e => <li key={e.code}>{e.name}{e.quantity!==null?` · ${e.quantity} ${e.unit??''}`:''}</li>)}</ul>}</CardContent></Card>)}</div></>}
    <div className="mt-8 flex flex-wrap gap-3"><Button asChild variant="outline"><Link href={cohortLink('/fees', c.cohort.slug)}>View fee plans</Link></Button>{c.accepting_applications&&<Button asChild><Link href={cohortLink('/apply', c.cohort.slug)}>Apply for this cohort</Link></Button>}</div>
  </>}
 </div>
}
