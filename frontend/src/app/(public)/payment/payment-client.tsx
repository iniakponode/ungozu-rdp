'use client'
import { useEffect, useState } from 'react'
import { getRdpPaymentProviders, getRdpPaymentSummary, initRdpPayment, type ApplicationStatus, type PaymentProviderList } from '@/lib/rdp-api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatMoney, ProgrammeStatus, RDPSectionHeading } from '@/components/rdp/rdp-ui'

export default function PaymentClient({refCode,paymentToken}:{refCode:string;paymentToken:string}){
 const [data,setData]=useState<ApplicationStatus|null>(null),[error,setError]=useState(''),[paying,setPaying]=useState<string|null>(null)
 const [providers,setProviders]=useState<Record<number,PaymentProviderList>>({})
 useEffect(()=>{
  if(!refCode||!paymentToken){setError('This payment link is incomplete. Use the private link sent with your admission offer.');return}
  getRdpPaymentSummary(refCode,paymentToken).then(async summary=>{
   setData(summary)
   const payable=summary.invoices.filter(i=>i.status==='pending'||i.status==='failed')
   const entries=await Promise.all(payable.map(async invoice=>{
    try{return [invoice.id,await getRdpPaymentProviders(refCode,paymentToken,invoice.id)] as const}catch{return [invoice.id,{active_environment:'test',allow_provider_selection:true,providers:[]}] as const}
   }))
   setProviders(Object.fromEntries(entries))
  }).catch(e=>setError(e instanceof Error?e.message:'Could not load payment record'))
 },[refCode,paymentToken])
 async function pay(invoiceId:number,provider?:string){
  const key=`${invoiceId}:${provider??'auto'}`;setPaying(key);setError('')
  try{const r=await initRdpPayment({application_ref:refCode,payment_token:paymentToken,invoice_id:invoiceId,provider});window.location.assign(r.authorization_url)}catch(e){setError(e instanceof Error?e.message:'Could not initialize payment');setPaying(null)}
 }
 return <div className="mx-auto max-w-4xl px-4 py-14 sm:px-6 lg:px-8"><RDPSectionHeading eyebrow="Secure payment" title="Programme fee payment" text="Payment is only available to admitted applicants. The amount and currency are calculated by the programme server from your approved fee plan."/>
 {error&&<p className="mt-6 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
 {!data&&!error&&<p className="mt-8 text-sm text-muted-foreground">Loading your admission and invoice record…</p>}
 {data&&<div className="mt-8 space-y-6"><Card><CardHeader><div className="flex flex-wrap items-center justify-between gap-3"><CardTitle>{data.full_name}</CardTitle><ProgrammeStatus status={data.status}/></div></CardHeader><CardContent className="text-sm"><p><b>Application:</b> {data.application_ref}</p>{data.fee_plan&&<><p className="mt-2"><b>Fee plan:</b> {data.fee_plan.name}</p><p className="mt-1 text-muted-foreground">{data.fee_plan.description}</p></>}{data.acceptance_deadline&&<p className="mt-2"><b>Acceptance/payment deadline:</b> {new Date(data.acceptance_deadline).toLocaleString('en-GB')}</p>}</CardContent></Card>
 <Card><CardHeader><CardTitle className="text-lg">Invoices</CardTitle></CardHeader><CardContent className="space-y-3">{data.invoices.map(i=>{const gateway=providers[i.id];const payable=i.status==='pending'||i.status==='failed';return <div key={i.id} className="rounded-lg border border-border p-4"><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-medium">Instalment {i.sequence}</p><div className="mt-1"><ProgrammeStatus status={i.status}/></div>{i.due_date&&<p className="mt-1 text-xs text-muted-foreground">Due {new Date(i.due_date+'T00:00:00').toLocaleDateString('en-GB')}</p>}</div><b className="text-lg">{formatMoney(i.amount_subunit,i.currency)}</b></div>
 {payable&&<div className="mt-4 border-t pt-4">{!gateway?<p className="text-xs text-muted-foreground">Checking available payment gateways…</p>:gateway.providers.length===0?<p className="rounded-md bg-amber-500/10 p-3 text-sm text-amber-800 dark:text-amber-300">Online payment is temporarily unavailable for {i.currency}. Please contact the programme team.</p>:<><div className="mb-3 flex flex-wrap items-center gap-2 text-xs"><span className="text-muted-foreground">Environment:</span><Badge variant="outline">{gateway.active_environment.toUpperCase()}</Badge></div>{gateway.allow_provider_selection&&gateway.providers.length>1?<div className="flex flex-wrap gap-2">{gateway.providers.map(p=><Button key={p.provider} disabled={paying!==null} onClick={()=>pay(i.id,p.provider)}>{paying===`${i.id}:${p.provider}`?'Opening checkout…':`Pay with ${p.display_name}`}</Button>)}</div>:<Button disabled={paying!==null} onClick={()=>pay(i.id,gateway.allow_provider_selection?gateway.providers[0]?.provider:undefined)}>{paying?.startsWith(`${i.id}:`)?'Opening checkout…':`Pay securely with ${gateway.providers[0]?.display_name??'available gateway'}`}</Button>}</>}</div>}
 </div>})}</CardContent></Card>
 <p className="text-xs leading-5 text-muted-foreground">Card and bank details are collected by the selected payment gateway, not by this website. Your programme record is updated only after server-side payment verification. A failed attempt never triggers an automatic charge through another provider.</p></div>}
 </div>
}
