import type { Metadata } from 'next'
import Link from 'next/link'
import { ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RDPSectionHeading } from '@/components/rdp/rdp-ui'

export const metadata: Metadata = { title: 'Programme Director | Ungozu R & D' }
export default function MentorPage(){return <div className="mx-auto max-w-5xl px-4 py-14 sm:px-6 lg:px-8"><RDPSectionHeading eyebrow="Programme Director & Lead Mentor" title="Dr. Iniakpokeikiye Peter Thompson" text="Lecturer, researcher and scholar-innovator working across responsible AI, natural language generation, low-resource computing, research commercialisation and societal impact."/>
<div className="mt-8 grid gap-6 lg:grid-cols-2"><Card><CardHeader><CardTitle>Mentoring approach</CardTitle></CardHeader><CardContent className="space-y-3 text-sm leading-6 text-muted-foreground"><p>The programme uses structured near-peer mentoring rather than positioning one person as the answer to every research problem. The mentor provides development planning, accountability, research-career guidance, feedback and access to a wider mentoring constellation when specialist expertise is needed.</p><p>The guiding progression is: demonstrate → practise together → participant leads with feedback → participant works independently → participant helps develop others.</p></CardContent></Card><Card><CardHeader><CardTitle>Academic context</CardTitle></CardHeader><CardContent className="space-y-3 text-sm leading-6 text-muted-foreground"><p>Dr. Thompson is a Lecturer/Researcher at Niger Delta University and an Honorary Research Fellow in Computing Science at the University of Aberdeen. His public academic profile and current work are maintained on his personal website.</p><Button asChild variant="outline"><a href="https://iniakpothompson.com" target="_blank" rel="noreferrer">View mentor profile <ExternalLink className="ml-2 h-4 w-4"/></a></Button></CardContent></Card></div>
<div className="mt-8"><Button asChild><Link href="/apply">View published programmes</Link></Button></div></div>}
