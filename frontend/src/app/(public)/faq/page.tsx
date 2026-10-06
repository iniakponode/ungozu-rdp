import type { Metadata } from 'next'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RDPSectionHeading } from '@/components/rdp/rdp-ui'

export const metadata: Metadata = { title: 'FAQ | Ungozu R & D Researcher Development Programme' }
const faqs=[
 ['Who is the programme for?','Early-career researchers, lecturers, recent PhD graduates, doctoral researchers approaching independence, and other emerging researchers who can demonstrate a clear development need and commitment to the 12-month process.'],
 ['Is the programme limited to Computer Science?','No. The mentoring framework is intentionally interdisciplinary. Discipline-specific needs may be supported through the wider mentoring constellation and invited specialists.'],
 ['How many researchers will be admitted?','The Founding Cohort is limited to 10 researchers.'],
 ['When do applications close?','Applications for the Founding Cohort run from 2 October 2026 to 2 November 2026. The programme begins on 2 December 2026.'],
 ['Can I apply for financial support?','Yes. Applicants may request a scholarship or subsidised place. Funding is limited, assessed separately, and not guaranteed.'],
 ['Does paying the fee guarantee publication or a grant?','No. The programme develops capability, accountability and opportunity readiness; research outcomes still depend on the participant’s work, research quality, journals/funders and other external factors.'],
 ['How are AI tools handled?','Participants learn responsible, transparent and verifiable use of generative AI. AI may support scholarly work, but it does not replace researcher accountability or research integrity.'],
 ['What happens after admission?','Accepted applicants receive a private admission/payment link. After the first required payment is verified, a participant account is created and the mentee receives a secure password-setup link for the programme portal.'],
 ['When is graduation?','The closing/graduation event is scheduled for Saturday, 27 November 2027, within the formal programme year ending 2 December 2027.'],
]
export default function FAQPage(){return <div className="mx-auto max-w-4xl px-4 py-14 sm:px-6 lg:px-8"><RDPSectionHeading eyebrow="FAQ" title="Common questions about the programme"/><div className="mt-8 space-y-4">{faqs.map(([q,a])=><Card key={q}><CardHeader><CardTitle className="text-base">{q}</CardTitle></CardHeader><CardContent className="text-sm leading-6 text-muted-foreground">{a}</CardContent></Card>)}</div><div className="mt-8"><Button asChild><Link href="/apply">Start application</Link></Button></div></div>}
