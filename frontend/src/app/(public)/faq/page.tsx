import type { Metadata } from 'next'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RDPSectionHeading } from '@/components/rdp/rdp-ui'
import { publishedCatalogues } from '@/lib/rdp-public-server'
import { chooseCatalogue, catalogueDuration, cohortLink } from '@/lib/rdp-catalogue'

export const metadata:Metadata = {title:'FAQ | Ungozu R & D'}

export default async function FAQPage({searchParams}:{searchParams:Promise<{cohort?:string}>}){
 const all=await publishedCatalogues()
 const c=chooseCatalogue(all,(await searchParams).cohort)
 const faqs=[
  ['Who can apply?', 'Emerging researchers, lecturers, recent PhD graduates and others who can demonstrate development needs and commitment to the programme.'],
  ['Does the programme cover different disciplines?', 'Programmes may be interdisciplinary or subject-specific. Read the published curriculum and entry information for the selected programme.'],
  ['How many places are available?',c?`The ${c.cohort.label} cohort has a published capacity of ${c.cohort.capacity}.`:'Each cohort has its own published capacity.'],
  ['What is the programme duration?',c?`${catalogueDuration(c)}. The cohort runs from ${c.cohort.start_date} to ${c.cohort.end_date}.`:'Duration is set separately for each published programme.'],
  ['When can I apply?',c?`Application dates: ${c.cohort.application_open_date} to ${c.cohort.application_deadline}. ${c.accepting_applications?'Applications are currently open.':'Applications are not currently open.'}`:'Refer to the published cohort announcement for application dates.'],
  ['Can I request financial support?', 'Applicants may request consideration for a scholarship or subsidised place. Awards are limited and separately assessed.'],
  ['Does payment guarantee publication or grants?', 'No. Programme participation develops research capacity but does not guarantee external outcomes.'],
  ['How are artificial intelligence tools handled?', 'Participants are expected to use AI transparently, verify results and uphold academic integrity.'],
  ['What happens after admission?', 'Approved applicants receive a private offer or quotation. After verified payment, eligible participants are enrolled and receive portal access.'],
  ['When is graduation?',c?`The scheduled graduation date for ${c.cohort.label} is ${c.cohort.graduation_date}.`:'Graduation dates are published per cohort.'],
 ]
 return <div className="mx-auto max-w-4xl px-4 py-14 sm:px-6 lg:px-8"><RDPSectionHeading eyebrow="FAQ" title="Common programme questions"/>{all.length>1&&<nav aria-label="Choose cohort" className="mt-6 flex flex-wrap gap-2">{all.map(x=><Button asChild size="sm" variant={x.cohort.id===c?.cohort.id?'default':'outline'} key={x.cohort.id}><Link href={cohortLink('/faq',x.cohort.slug)}>{x.cohort.label}</Link></Button>)}</nav>}<div className="mt-8 space-y-4">{faqs.map(([q,a])=><Card key={q}><CardHeader><CardTitle className="text-base">{q}</CardTitle></CardHeader><CardContent className="text-sm leading-6 text-muted-foreground">{a}</CardContent></Card>)}</div>{c?.accepting_applications&&<div className="mt-8"><Button asChild><Link href={cohortLink('/apply',c.cohort.slug)}>Start application</Link></Button></div>}</div>
}
