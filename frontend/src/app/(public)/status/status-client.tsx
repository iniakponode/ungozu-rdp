'use client'
import { FormEvent, useEffect, useState } from 'react'
import Link from 'next/link'
import QuotationReview from '@/components/rdp/quotation-review'
import { getRdpApplicationStatus, type ApplicationStatus } from '@/lib/rdp-api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ProgrammeStatus, formatMoney, RDPSectionHeading } from '@/components/rdp/rdp-ui'

export default function StatusClient({initialRef,initialToken}:{initialRef:string;initialToken:string}){
 const [ref,setRef]=useState(initialRef),[token,setToken]=useState(initialToken),[data,setData]=useState<ApplicationStatus|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false)
 async function load(e?:FormEvent){e?.preventDefault();if(!ref||!token)return;setBusy(true);setError('');try{setData(await getRdpApplicationStatus(ref,token))}catch(err){setError(err instanceof Error?err.message:'Could not retrieve status')}finally{setBusy(false)}}
 useEffect(()=>{if(initialRef&&initialToken){load()}},[])
 const scholarship=`/scholarship?ref=${encodeURIComponent(ref)}&token=${encodeURIComponent(token)}`
 return <div className="mx-auto max-w-4xl px-4 py-14 sm:px-6 lg:px-8"><RDPSectionHeading eyebrow="Application portal" title="Check your application status" text="Use your private application-status link to check progress. If checking manually, enter your application reference and private access code."/>
  {!data&&<form onSubmit={load} className="mt-8 max-w-2xl rounded-xl border border-border bg-card p-6 space-y-4"><div><Label>Application reference</Label><Input value={ref} onChange={e=>setRef(e.target.value)} placeholder="URD-2026-…"/></div><div><Label>Private access code</Label><Input value={token} onChange={e=>setToken(e.target.value)} type="password"/></div>{error&&<p className="text-sm text-destructive">{error}</p>}<Button disabled={busy||!ref||!token}>{busy?'Checking…':'Check status'}</Button></form>}
  {data&&<div className="mt-8 space-y-6"><Card><CardHeader><div className="flex flex-wrap items-center justify-between gap-3"><CardTitle>{data.full_name}</CardTitle><ProgrammeStatus status={data.status}/></div></CardHeader><CardContent className="space-y-3 text-sm"><p><b>Reference:</b> {data.application_ref}</p><p><b>Cohort:</b> {data.cohort_label}</p>{data.scholarship_status&&<p><b>Scholarship:</b> <ProgrammeStatus status={data.scholarship_status}/></p>}{data.acceptance_deadline&&<p><b>Acceptance/payment deadline:</b> {new Date(data.acceptance_deadline).toLocaleString('en-GB')}</p>}</CardContent></Card>
   {data.status==='quote_offered' && <QuotationReview reference={ref} accessToken={token} />}
   {data.fee_plan&&<Card><CardHeader><CardTitle className="text-lg">Approved fee plan</CardTitle></CardHeader><CardContent><p className="font-medium">{data.fee_plan.name}</p><p className="mt-1 text-2xl font-semibold">{formatMoney(data.fee_plan.total_amount_subunit,data.fee_plan.currency)}</p><p className="mt-2 text-sm text-muted-foreground">{data.fee_plan.description}</p></CardContent></Card>}
   {data.invoices.length>0&&<Card><CardHeader><CardTitle className="text-lg">Invoices</CardTitle></CardHeader><CardContent className="space-y-2">{data.invoices.map(i=><div key={i.id} className="flex items-center justify-between rounded-md border border-border p-3 text-sm"><span>Instalment {i.sequence} · <ProgrammeStatus status={i.status}/></span><b>{formatMoney(i.amount_subunit,i.currency)}</b></div>)}</CardContent></Card>}
   <div className="flex flex-wrap gap-3">{!data.scholarship_status&&<Button asChild variant="outline"><Link href={scholarship}>Request scholarship support</Link></Button>}<Button variant="outline" onClick={()=>setData(null)}>Check another application</Button></div>
  </div>}
 </div>
}
