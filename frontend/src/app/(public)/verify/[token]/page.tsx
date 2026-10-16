import Link from 'next/link'
import {verifiedCertificate} from '@/lib/server/rdp-certificate'
import { Card,CardContent,CardHeader,CardTitle } from '@/components/ui/card'
export const dynamic='force-dynamic'
export default async function Verify({params}:{params:Promise<{token:string}>}){
 const {token}=await params;const c=await verifiedCertificate(token)
 return <main className="mx-auto max-w-2xl px-4 py-14"><Card><CardHeader><CardTitle>Ungozu R & D · Certificate verification</CardTitle></CardHeader><CardContent className="space-y-4">{!c?<p>Certificate could not be verified. Check that the link is correct or contact programme administration.</p>:<><p className={c.valid?'font-semibold text-green-700':'font-semibold text-red-700'}>{c.valid?'Verified certificate':'Certificate revoked — not valid'}</p><dl className="grid grid-cols-[auto_1fr] gap-3 text-sm"><dt>Number</dt><dd className="font-mono break-all">{c.certificate_number}</dd><dt>Researcher</dt><dd>{c.recipient_name}</dd><dt>Programme</dt><dd>{c.programme_title}</dd><dt>Cohort</dt><dd>{c.cohort_label}</dd><dt>Duration</dt><dd>{c.duration??'—'}</dd><dt>Issued</dt><dd>{new Date(c.issued_at).toLocaleDateString('en-GB')}</dd></dl>{c.valid&&<Link className="text-primary underline" href={`/certificate/${token}`}>View printable certificate</Link>}</>}</CardContent></Card></main>
}
