'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getRdpCohort, type Cohort } from '@/lib/rdp-api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { formatMoney, RDPSectionHeading } from '@/components/rdp/rdp-ui'

export default function FeesPage(){
 const [cohort,setCohort]=useState<Cohort|null>(null)
 useEffect(()=>{getRdpCohort().then(setCohort).catch(()=>{})},[])
 const fees=cohort?.fee_plans ?? []
 return <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
  <RDPSectionHeading eyebrow="Fees & access" title="Founding-cohort fee options" text="The fee supports a year of structured development, cohort learning, mentoring, quarterly reviews, research-development resources and programme administration. Scholarship/subsidised places are considered separately."/>
  <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">{fees.length?fees.map(f=><Card key={f.id}><CardHeader><p className="text-xs font-semibold uppercase tracking-wider text-primary">{f.region.replaceAll('_',' ')}</p><CardTitle className="text-base">{f.name}</CardTitle></CardHeader><CardContent><p className="text-3xl font-semibold">{formatMoney(f.total_amount_subunit,f.currency)}</p><p className="mt-2 text-sm text-muted-foreground">{f.description}</p>{f.installment_count>1&&<p className="mt-3 text-xs text-muted-foreground">{f.installment_count} instalments · {formatMoney(f.installment_amount_subunit,f.currency)} nominal instalment</p>}</CardContent></Card>):<p className="text-sm text-muted-foreground">Fee plans are loading from the programme system.</p>}</div>
  <div className="mt-10 grid gap-6 lg:grid-cols-2"><Card><CardHeader><CardTitle>Scholarship and subsidised places</CardTitle></CardHeader><CardContent className="space-y-3 text-sm leading-6 text-muted-foreground"><p>Applicants with genuine financial constraints may request a full or partial scholarship/subsidised place. Awards are limited and are assessed separately from academic/programme fit.</p><p>Requesting support does not guarantee an award, and approved support is reflected in the applicant’s invoice before payment begins.</p></CardContent></Card><Card><CardHeader><CardTitle>What is not included</CardTitle></CardHeader><CardContent className="text-sm leading-6 text-muted-foreground">The programme does not guarantee publication, grants, employment or admissions; and it does not include unlimited manuscript editing, ghost-writing, or doing a participant’s research/analysis on their behalf.</CardContent></Card></div>
  <div className="mt-8 flex flex-wrap gap-3"><Button asChild><Link href="/apply">Apply for the programme</Link></Button><Button asChild variant="outline"><Link href="/faq">Read FAQs</Link></Button></div>
 </div>
}
