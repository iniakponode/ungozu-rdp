import type { Metadata } from 'next'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RDPSectionHeading } from '@/components/rdp/rdp-ui'
import { publishedCatalogues } from '@/lib/rdp-public-server'
import { catalogueTitle, chooseCatalogue, cohortLink, money } from '@/lib/rdp-catalogue'

export const metadata: Metadata = {title:'Packages and fees | Ungozu R & D'}

export default async function FeesPage({searchParams}:{searchParams:Promise<{cohort?:string}>}){
 const catalogues=await publishedCatalogues()
 const c=chooseCatalogue(catalogues,(await searchParams).cohort)
 const packages=new Map(c?.packages.map(p=>[p.id,p])??[])
 return <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
 <RDPSectionHeading eyebrow="Fees and access" title={c?`Packages and fees — ${catalogueTitle(c)}`:'Published programme fees'} text="Compare programme packages, fees and instalment options below. Applications for scholarship support are reviewed separately."/>
 {catalogues.length>1&&<nav aria-label="Choose cohort" className="mt-6 flex flex-wrap gap-2">{catalogues.map(x=><Button asChild size="sm" variant={c?.cohort.id===x.cohort.id?'default':'outline'} key={x.cohort.id}><Link href={cohortLink('/fees',x.cohort.slug)}>{x.cohort.label}</Link></Button>)}</nav>}
 {!c?<p className="mt-8 rounded-lg border p-6 text-sm text-muted-foreground">No published fee schedules are currently available.</p>:<>
 <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">{c.fee_plans.length?c.fee_plans.map(f=><Card key={f.id}><CardHeader><p className="text-xs font-semibold uppercase tracking-wider text-primary">{f.region.replaceAll('_',' ')}</p><CardTitle>{f.name}</CardTitle></CardHeader><CardContent><p className="text-3xl font-semibold">{money(f.total_amount_subunit,f.currency)}</p>{f.description&&<p className="mt-2 text-sm text-muted-foreground">{f.description}</p>}{f.package_id!=null&&packages.has(f.package_id)&&<div className="mt-4 text-sm"><p className="font-semibold">{packages.get(f.package_id)?.name}</p><ul className="mt-1 list-disc pl-5 text-muted-foreground">{packages.get(f.package_id)?.entitlements.map(e=><li key={e.code}>{e.name}{e.quantity!==null?` · ${e.quantity} ${e.unit??''}`:''}</li>)}</ul></div>}{f.installments.length>0&&<div className="mt-4 text-sm"><p className="font-medium">Instalment schedule</p><ul className="mt-2 space-y-1 text-muted-foreground">{f.installments.map(x=><li key={x.sequence_number}>{x.sequence_number}. {money(x.amount_subunit,f.currency)} · {x.due_offset_days===0?'due on the offer date':`due ${x.due_offset_days} day(s) after the offer date`}</li>)}</ul></div>}</CardContent></Card>):<p className="text-sm text-muted-foreground">No currently available fee plans for this cohort.</p>}</div>
 <div className="mt-8 flex flex-wrap gap-3">{c.accepting_applications&&<Button asChild><Link href={cohortLink('/apply',c.cohort.slug)}>Apply for this cohort</Link></Button>}<Button asChild variant="outline"><Link href={cohortLink('/programme',c.cohort.slug)}>View curriculum</Link></Button></div>
 </>}
 <div className="mt-10 rounded-xl border p-6 text-sm leading-6 text-muted-foreground">Applications for financial assistance are assessed separately. Programme fees do not guarantee publication, grant awards or employment, and do not include ghost-writing or outsourced research.</div>
 </div>
}
