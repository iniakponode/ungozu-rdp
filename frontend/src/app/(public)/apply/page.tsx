'use client'

import { FormEvent, useEffect, useState } from 'react'
import Link from 'next/link'
import { getRdpCatalogues, submitRdpApplication } from '@/lib/rdp-api'
import { catalogueDuration, catalogueTitle, type Catalogue } from '@/lib/rdp-catalogue'
import { ApplicationPackagePreference } from '@/components/rdp/application-package-preference'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { RDPSectionHeading } from '@/components/rdp/rdp-ui'

const initial={full_name:'',email:'',country:'Nigeria',institution:'',career_stage:'',discipline:'',research_interests:'',goals:'',challenges:'',current_outputs:'',commitment:'',scholarship_interest:false,referral_source:'',consent:false}

export default function ApplyPage(){
 const [form,setForm]=useState(initial),[busy,setBusy]=useState(false),[error,setError]=useState(''),[receipt,setReceipt]=useState<{application_ref:string;access_token:string;status:string;message:string}|null>(null)
 const [catalogues,setCatalogues]=useState<Catalogue[]>([]),[cohortSlug,setCohortSlug]=useState(''),[catalogueLoaded,setCatalogueLoaded]=useState(false)
 const [preferredPackage,setPreferredPackage]=useState<number|null>(null),[preferredPlan,setPreferredPlan]=useState<number|null>(null)
 useEffect(()=>{let live=true;getRdpCatalogues().then(c=>{if(!live)return;setCatalogues(c);const query=new URLSearchParams(window.location.search).get('cohort');const selected=c.find(x=>x.cohort.slug===query)||c.find(x=>x.accepting_applications)||c[0];setCohortSlug(selected?.cohort.slug||'')}).catch(()=>{}).finally(()=>{if(live)setCatalogueLoaded(true)});return()=>{live=false}},[])
 const selected=catalogues.find(x=>x.cohort.slug===cohortSlug)
 const set=(k:string,v:string|boolean)=>setForm(x=>({...x,[k]:v}))
 async function submit(e:FormEvent){
  e.preventDefault();setError('')
  if(!selected?.accepting_applications){setError('Select a cohort currently open for applications.');return}
  // Programme Builder applicants choose a preferred package and matching plan.
  // Their preference is not a confirmed admission or place reservation.
  const selectablePlans = selected.fee_plans.filter(p=>selected.packages.some(pkg=>pkg.id===p.package_id))
  if(selectablePlans.length && (!preferredPackage || !preferredPlan ||
     !selectablePlans.some(p=>p.id===preferredPlan && p.package_id===preferredPackage))){
     setError('Choose your preferred mentoring package and payment option.');return
  }
  setBusy(true)
  try{const r=await submitRdpApplication({...form,cohort_slug:selected.cohort.slug,
    preferred_package_id:preferredPackage,preferred_fee_plan_id:preferredPlan});setReceipt(r)}
  catch(err){setError(err instanceof Error?err.message:'Could not submit application')}finally{setBusy(false)}
 }
 if(receipt){const status=`/status?ref=${encodeURIComponent(receipt.application_ref)}&token=${encodeURIComponent(receipt.access_token)}`; const scholarship=`/scholarship?ref=${encodeURIComponent(receipt.application_ref)}&token=${encodeURIComponent(receipt.access_token)}`; return <div className="mx-auto max-w-3xl px-4 py-14 sm:px-6"><Card><CardHeader><CardTitle>Application received</CardTitle></CardHeader><CardContent className="space-y-4"><p className="text-sm text-muted-foreground">Thank you. Your application has been recorded.</p><div className="rounded-lg border border-border bg-muted/30 p-4"><p className="text-xs uppercase tracking-wider text-muted-foreground">Application reference</p><p className="mt-1 font-mono text-lg font-semibold">{receipt.application_ref}</p></div><p className="text-sm text-muted-foreground">Use the private link below to track your application and any subsequent offer. A confirmation email should arrive shortly; if you do not see it, check your Spam or Junk folder. Keep your private link secure.</p><div className="flex flex-wrap gap-3"><Button asChild><Link href={status}>View application status</Link></Button>{form.scholarship_interest&&<Button asChild variant="outline"><Link href={scholarship}>Complete scholarship request</Link></Button>}</div></CardContent></Card></div>}
 return <div className="mx-auto max-w-4xl px-4 py-14 sm:px-6 lg:px-8">
  <RDPSectionHeading eyebrow="Programme admissions" title="Participant application" text="Select an available cohort and provide information about your research background, goals, commitment and development needs."/>
  <form onSubmit={submit} className="mt-8 space-y-6">
   <Card><CardHeader><CardTitle className="text-lg">Choose a programme and cohort</CardTitle></CardHeader><CardContent className="space-y-3"><Label htmlFor="selected-cohort">Programme cohort</Label><select id="selected-cohort" className="w-full rounded-md border border-input bg-background p-3 text-sm" value={cohortSlug} onChange={e=>{setCohortSlug(e.target.value);setPreferredPackage(null);setPreferredPlan(null)}} required><option value="">Select a cohort…</option>{catalogues.map(c=><option key={c.cohort.id} value={c.cohort.slug}>{catalogueTitle(c)} — {c.cohort.label}{c.accepting_applications?' (open)':' (closed)'}</option>)}</select>{selected&&<div className="text-sm text-muted-foreground"><p>Duration: {catalogueDuration(selected)}</p><p>Start: {selected.cohort.start_date} · Application deadline: {selected.cohort.application_deadline}</p>{!selected.accepting_applications&&<p className="mt-2 text-destructive">Applications are not currently open for this cohort.</p>}</div>}{catalogueLoaded&&catalogues.length===0&&<p className="text-sm text-destructive">No published cohorts are available. Please try again later.</p>}</CardContent></Card>
   {selected && selected.packages.length>0 && <ApplicationPackagePreference
     catalogue={selected} packageId={preferredPackage} planId={preferredPlan}
     onPackageChange={id=>{setPreferredPackage(id);setPreferredPlan(null)}}
     onPlanChange={setPreferredPlan} />}
   <Card><CardHeader><CardTitle className="text-lg">About you</CardTitle></CardHeader><CardContent className="grid gap-5 sm:grid-cols-2">
    <div><Label htmlFor="full_name">Full name</Label><Input id="full_name" required value={form.full_name} onChange={e=>set('full_name',e.target.value)}/></div>
    <div><Label htmlFor="email">Email</Label><Input id="email" type="email" required value={form.email} onChange={e=>set('email',e.target.value)}/></div>
    <div><Label htmlFor="country">Country</Label><Input id="country" required value={form.country} onChange={e=>set('country',e.target.value)}/></div>
    <div><Label htmlFor="institution">Institution / organisation</Label><Input id="institution" required value={form.institution} onChange={e=>set('institution',e.target.value)}/></div>
    <div><Label htmlFor="career_stage">Career stage</Label><Input id="career_stage" required placeholder="e.g. Lecturer, postdoc, recent PhD, doctoral researcher" value={form.career_stage} onChange={e=>set('career_stage',e.target.value)}/></div>
    <div><Label htmlFor="discipline">Discipline / field</Label><Input id="discipline" required value={form.discipline} onChange={e=>set('discipline',e.target.value)}/></div>
   </CardContent></Card>
   <Card><CardHeader><CardTitle className="text-lg">Research development</CardTitle></CardHeader><CardContent className="space-y-5">
    <div><Label htmlFor="research_interests">Research interests</Label><Textarea id="research_interests" required minLength={20} rows={5} value={form.research_interests} onChange={e=>set('research_interests',e.target.value)} placeholder="What questions, problems or fields currently shape your research?"/></div>
    <div><Label htmlFor="goals">What would you like to achieve during this programme?</Label><Textarea id="goals" required minLength={20} rows={5} value={form.goals} onChange={e=>set('goals',e.target.value)} placeholder="Research capability, publications, grants, collaborations, methods, impact, career goals…"/></div>
    <div><Label htmlFor="challenges">What are your most important current research-development challenges?</Label><Textarea id="challenges" required minLength={20} rows={5} value={form.challenges} onChange={e=>set('challenges',e.target.value)}/></div>
    <div><Label htmlFor="current_outputs">Current research outputs (optional)</Label><Textarea id="current_outputs" rows={4} value={form.current_outputs} onChange={e=>set('current_outputs',e.target.value)} placeholder="Papers, thesis, datasets, proposals, projects, conference work, software, policy outputs…"/></div>
    <div><Label htmlFor="commitment">How will you make time for and contribute to the programme?</Label><Textarea id="commitment" required minLength={20} rows={5} value={form.commitment} onChange={e=>set('commitment',e.target.value)}/></div>
   </CardContent></Card>
   <Card><CardHeader><CardTitle className="text-lg">Access and declaration</CardTitle></CardHeader><CardContent className="space-y-4">
    <label className="flex gap-3 text-sm"><input type="checkbox" checked={form.scholarship_interest} onChange={e=>set('scholarship_interest',e.target.checked)} className="mt-1"/><span>I would like to request consideration for a scholarship or subsidised place.</span></label>
    <div><Label htmlFor="referral">How did you hear about the programme? (optional)</Label><Input id="referral" value={form.referral_source} onChange={e=>set('referral_source',e.target.value)}/></div>
    <label className="flex gap-3 text-sm"><input required type="checkbox" checked={form.consent} onChange={e=>set('consent',e.target.checked)} className="mt-1"/><span>I confirm that the information supplied is accurate and consent to its use for programme selection, administration and communication in accordance with the programme privacy notice and terms.</span></label>
   </CardContent></Card>
   {error&&<p className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
   <div className="flex flex-wrap items-center gap-3"><Button disabled={busy||!selected?.accepting_applications} type="submit" size="lg">{busy?'Submitting…':'Submit application'}</Button><p className="text-xs text-muted-foreground">Do not submit more than once with the same email address.</p></div>
  </form>
 </div>
}
