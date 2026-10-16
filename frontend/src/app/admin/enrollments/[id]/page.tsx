'use client'
import { CompletionAdmin } from '@/components/rdp/completion-admin'
import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { getRDPEnrollment, reviewRDPCheckIn, reviewRDPDevelopmentPlan, type RDPEnrollmentAdminDetail } from '@/lib/rdp-admin-api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'

export default function RDPEnrollmentDetailPage(){
 const id=Number(useParams<{id:string}>().id),[data,setData]=useState<RDPEnrollmentAdminDetail|null>(null),[planNotes,setPlanNotes]=useState(''),[feedback,setFeedback]=useState<Record<number,string>>({})
 const load=async()=>{const d=await getRDPEnrollment(id);setData(d);setPlanNotes(d.development_plan?.mentor_notes??'');setFeedback(Object.fromEntries(d.checkins.map(c=>[c.id,c.mentor_feedback??''])))}
 useEffect(()=>{load().catch(()=>toast.error('Failed to load mentoring record'))},[id])
 if(!data)return <p>Loading…</p>
 const savePlan=async()=>{try{await reviewRDPDevelopmentPlan(id,{mentor_notes:planNotes,status:'reviewed'});toast.success('IRDP feedback saved');await load()}catch(e){toast.error(e instanceof Error?e.message:'Could not save IRDP feedback')}}
 const saveCheck=async(checkinId:number)=>{try{await reviewRDPCheckIn(checkinId,{mentor_feedback:feedback[checkinId]??'',status:'reviewed'});toast.success('Check-in reviewed');await load()}catch(e){toast.error(e instanceof Error?e.message:'Could not save feedback')}}
 return <div className="space-y-6"><div><div className="flex flex-wrap items-center gap-3"><h1 className="text-2xl font-bold">{data.enrollment.full_name}</h1><Badge variant="outline">{data.enrollment.status}</Badge></div><p className="mt-1 text-sm text-muted-foreground">{data.enrollment.email} · {data.cohort.label}</p></div>
 <Card><CardHeader><CardTitle>Individual Researcher Development Plan</CardTitle></CardHeader><CardContent className="space-y-4">{data.development_plan?<><div className="grid gap-4 md:grid-cols-2">{[['Researcher identity',data.development_plan.researcher_identity],['Programme development goal',data.development_plan.twelve_month_goal],['Publication goal',data.development_plan.publication_goal],['Methods/data goal',data.development_plan.methods_goal],['Funding goal',data.development_plan.funding_goal],['Network goal',data.development_plan.network_goal],['Impact goal',data.development_plan.impact_goal]].map(([h,t])=><div key={h} className="rounded-md border p-4"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{h}</p><p className="mt-2 whitespace-pre-wrap text-sm">{t||'—'}</p></div>)}</div><div><Label>Mentor feedback</Label><Textarea rows={5} value={planNotes} onChange={e=>setPlanNotes(e.target.value)} placeholder="Feedback, priorities and next actions"/></div><Button onClick={savePlan}>Save IRDP feedback</Button></>:<p className="text-sm text-muted-foreground">No development plan has been created yet.</p>}</CardContent></Card>
 <Card><CardHeader><CardTitle>Monthly check-ins</CardTitle></CardHeader><CardContent className="space-y-5">{data.checkins.length?data.checkins.map(c=><div key={c.id} className="rounded-lg border border-border p-4"><div className="flex items-center justify-between"><h3 className="font-semibold">Month {c.month_number}</h3><Badge variant="outline">{c.status}</Badge></div><div className="mt-4 grid gap-4 md:grid-cols-2">{[['Progress',c.progress_summary],['Outputs',c.outputs_this_month],['Obstacles',c.obstacles],['Next actions',c.next_actions],['Support requested',c.support_requested]].map(([h,t])=><div key={h}><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{h}</p><p className="mt-1 whitespace-pre-wrap text-sm">{t||'—'}</p></div>)}</div><div className="mt-4"><Label>Mentor feedback</Label><Textarea rows={4} value={feedback[c.id]??''} onChange={e=>setFeedback(x=>({...x,[c.id]:e.target.value}))}/></div><Button size="sm" className="mt-3" onClick={()=>saveCheck(c.id)}>Mark reviewed & save feedback</Button></div>):<p className="text-sm text-muted-foreground">No monthly check-ins submitted yet.</p>}</CardContent></Card>
 <CompletionAdmin enrollmentId={id}/><Card><CardHeader><CardTitle>Invoices</CardTitle></CardHeader><CardContent className="space-y-2">{data.invoices.map(i=><div key={i.id} className="flex items-center justify-between rounded border p-3 text-sm"><span>Instalment {i.sequence} · {i.status}</span><b>{new Intl.NumberFormat('en',{style:'currency',currency:i.currency}).format(i.amount_subunit/100)}</b></div>)}</CardContent></Card>
 </div>
}
