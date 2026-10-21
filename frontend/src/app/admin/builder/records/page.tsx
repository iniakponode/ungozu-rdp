'use client'
import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { AlertTriangle, Archive, RotateCcw, Trash2, Search, ShieldCheck } from 'lucide-react'
import { fetchBuilder, type BuilderData, type Cohort, type Version, type Programme } from '@/lib/rdp-builder-api'
import { userErrorMessage } from '@/lib/api-errors'

type Kind = 'programmes'|'versions'|'cohorts'|'criteria'
type Criterion = {id:number;programme_version_id:number;code:string;title:string;required:boolean}
type Archived = {record_type:Kind;record_id:number;archived_at:string;previous_status:string|null}
type Action = 'DELETE'|'ARCHIVE'|'RESTORE'
const initial:BuilderData = {programmes:[],versions:[],cohorts:[],modules:[],items:[],packages:[],entitlements:[],fee_plans:[],installments:[]}
const kinds: {value:Kind;label:string}[] = [{value:'cohorts',label:'Cohorts'},{value:'versions',label:'Programme versions'},{value:'programmes',label:'Programmes'},{value:'criteria',label:'Assessment criteria'}]
function displayDate(v:string|null|undefined){if(!v)return 'Not set';const d=new Date(`${v.slice(0,10)}T12:00:00`);return Number.isNaN(d.getTime())?v:new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric'}).format(d)}
function statusLabel(value:string){return value.replace(/_/g,' ')}
export default function RecordLifecyclePage(){
 const [data,setData]=useState<BuilderData>(initial)
 const [archives,setArchives]=useState<Archived[]>([])
 const [criteria,setCriteria]=useState<Criterion[]>([])
 const [selected,setSelected]=useState<Kind>('cohorts')
 const [reason,setReason]=useState('')
 const [query,setQuery]=useState('')
 const [busy,setBusy]=useState(false)
 const [loading,setLoading]=useState(true)
 const [error,setError]=useState('')
 const [message,setMessage]=useState('')
 const [pending,setPending]=useState<{kind:Kind;id:number;action:Action;name:string}|null>(null)
 const [confirmText,setConfirmText]=useState('')
 const refresh=useCallback(async()=>{
   const [builder,a,c]=await Promise.all([fetchBuilder(),fetch('/api/rdp-admin/builder/records/archives',{cache:'no-store'}),fetch('/api/rdp-admin/builder/records/criteria',{cache:'no-store'})])
   if(!a.ok||!c.ok)throw new Error('Unable to load lifecycle records; check administrator access and retry')
   setData(builder);setArchives(await a.json() as Archived[]);setCriteria(await c.json() as Criterion[])
 },[])
 useEffect(()=>{let live=true;void refresh().catch(e=>{if(live)setError(userErrorMessage(e,'Unable to load records'))}).finally(()=>{if(live)setLoading(false)});return()=>{live=false}},[refresh])
 const rows=useMemo(()=>(selected==='programmes'?data.programmes:selected==='versions'?data.versions:selected==='cohorts'?data.cohorts:criteria).filter(row=>{
   const name='name' in row?row.name:row.title
   return `${row.id} ${name}`.toLowerCase().includes(query.trim().toLowerCase())
 }),[selected,data,criteria,query])
 const isArchived=(k:Kind,id:number)=>archives.some(a=>a.record_type===k&&a.record_id===id)
 const nameOf=(kind:Kind,id:number)=>{
   const list=kind==='programmes'?data.programmes:kind==='versions'?data.versions:kind==='cohorts'?data.cohorts:criteria
   const record=list.find(x=>x.id===id)
   return record?('name' in record?record.name:record.title):`${kind} #${id}`
 }
 const versionOf=(id:number|null|undefined)=>data.versions.find(v=>v.id===id)
 const programmeOf=(id:number|null|undefined)=>data.programmes.find(p=>p.id===id)
 function openAction(kind:Kind,id:number,action:Action){
   setError('');setMessage('')
   if(reason.trim().length<5){setError('Please enter an administrative reason containing at least five characters.');return}
   setConfirmText('');setPending({kind,id,action,name:nameOf(kind,id)})
 }
 async function perform(){
   if(!pending||confirmText!==pending.action||busy)return
   const {kind,id,action}=pending
   setBusy(true);setError('')
   try{
     const result=await fetch(`/api/rdp-admin/builder/records/${kind}/${id}${action==='ARCHIVE'?'/archive':action==='RESTORE'?'/restore':''}`,{
       method:action==='DELETE'?'DELETE':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reason:reason.trim(),confirmation:action})
     })
     if(!result.ok){const payload=await result.json().catch(()=>({detail:'Operation rejected'}));const detail=payload.detail;throw Error(typeof detail==='string'?detail:'Operation rejected by server safeguards')}
     setPending(null);setConfirmText('');await refresh()
     setMessage(`${action==='DELETE'?'Deleted':action==='ARCHIVE'?'Archived':'Restored'} ${kind} #${id} successfully.`)
   }catch(e){setError(userErrorMessage(e,'Unable to complete operation'))}finally{setBusy(false)}
 }
 const selectedLabel=kinds.find(k=>k.value===selected)?.label??'Records'
 return <div className="space-y-6">
  <div className="space-y-2">
   <Link className="text-sm text-muted-foreground underline-offset-4 hover:underline" href="/admin/builder">← Back to Programme Builder</Link>
   <div className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-2xl font-bold tracking-tight">Manage programme records</h1><p className="mt-1 max-w-3xl text-sm text-muted-foreground">Remove unused drafts, archive historical records and restore archived configuration. Actions are audited and validated by the server.</p></div><span className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs text-muted-foreground"><ShieldCheck className="h-4 w-4"/>Administrator-only</span></div>
  </div>
  <div className="rounded-lg border bg-card p-4 space-y-4">
    <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <label className="space-y-1.5 text-sm font-medium">Record type<select className="block w-full rounded-md border bg-background px-3 py-2" value={selected} onChange={e=>{setSelected(e.target.value as Kind);setQuery('')}}>{kinds.map(k=><option key={k.value} value={k.value}>{k.label}</option>)}</select></label>
      <label className="space-y-1.5 text-sm font-medium">Find a record<div className="relative"><Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground"/><input aria-label="Search records" className="w-full rounded-md border bg-background py-2 pl-9 pr-3" placeholder="Search by name or record ID" value={query} onChange={e=>setQuery(e.target.value)}/></div></label>
    </div>
    <label className="block space-y-1.5 text-sm font-medium">Reason for action<input className="block w-full rounded-md border bg-background px-3 py-2 font-normal" value={reason} maxLength={500} onChange={e=>setReason(e.target.value)} placeholder="Required for archive, restore or deletion (minimum 5 characters)"/><span className="block text-xs font-normal text-muted-foreground">Recorded in the lifecycle audit history. No change occurs until you confirm an action.</span></label>
  </div>
  {error&&<div role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950/30 dark:text-red-200">{error}</div>}
  {message&&<div role="status" className="rounded-md border border-green-300 bg-green-50 p-3 text-sm text-green-800 dark:bg-green-950/30 dark:text-green-200">{message}</div>}
  <section className="space-y-3" aria-label={selectedLabel}>
   <div className="flex items-center justify-between gap-3"><h2 className="text-lg font-semibold">{selectedLabel}</h2><span className="text-xs text-muted-foreground">{rows.length} shown</span></div>
   {loading?<p className="text-sm text-muted-foreground">Loading records…</p>:rows.length===0?<p className="rounded-lg border p-5 text-sm text-muted-foreground">No matching records found.</p>:rows.map(row=>{
     const archived=isArchived(selected,row.id)
     const status='status' in row?row.status:undefined
     const published='is_published' in row?row.is_published:false
     const version=selected==='cohorts'?versionOf((row as Cohort).programme_version_id):selected==='versions'?row as Version:selected==='criteria'?versionOf((row as Criterion).programme_version_id):undefined
     const programme=selected==='programmes'?row as Programme:programmeOf(version?.programme_id)
     const criteriaParentDraft=selected!=='criteria'||(version?.status==='draft'&&!version.published_at)
     const neverPublished=selected==='criteria'?criteriaParentDraft:selected==='versions'?status==='draft'&&!(row as Version).published_at:status==='draft'&&!published
     const canDelete=!archived&&neverPublished
     const cohort=selected==='cohorts'?row as Cohort:null
     return <article key={`${selected}-${row.id}`} className="rounded-lg border bg-card p-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0 space-y-1"><div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">#{row.id} · {'name' in row?row.name:row.title}</h3><span className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground">{archived?'Archived':status?statusLabel(status):'Criterion'}</span>{published&&<span className="rounded-full border px-2 py-0.5 text-xs">Public</span>}</div><p className="text-xs text-muted-foreground">{programme&&selected!=='programmes'?`Programme: ${programme.name} · `:''}{version?`Version ${version.version_number}: ${version.title}`:selected==='programmes'?`Programme ID: ${row.id}`:''}</p></div></div>
      {cohort&&<div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2 lg:grid-cols-4"><span>Opens: {displayDate(cohort.application_open_date)}</span><span>Deadline: {displayDate(cohort.application_deadline)}</span><span>Starts: {displayDate(cohort.start_date)}</span><span>Capacity: {cohort.capacity}</span></div>}
      {selected==='criteria'&&<p className="text-xs text-muted-foreground">Criterion code: {(row as Criterion).code} · {(row as Criterion).required?'Required':'Optional'}</p>}
      <div className="flex flex-wrap items-center gap-2 border-t pt-3"><button className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-40 hover:bg-accent" disabled={busy||!canDelete} title={!canDelete?'Only never-published, unarchived draft records may be deleted; dependencies can still block deletion':''} onClick={()=>openAction(selected,row.id,'DELETE')}><Trash2 className="h-4 w-4"/>Delete draft</button><button className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm disabled:opacity-40 hover:bg-accent" disabled={busy||archived} onClick={()=>openAction(selected,row.id,'ARCHIVE')}><Archive className="h-4 w-4"/>Archive</button><button className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm disabled:opacity-40 hover:bg-accent" disabled={busy||!archived} onClick={()=>openAction(selected,row.id,'RESTORE')}><RotateCcw className="h-4 w-4"/>Restore</button></div>
      {cohort&&!archived&&<p className="text-xs text-muted-foreground">Application counts and references are verified by the server before any change.</p>}
     </article>
   })}
  </section>
  <section className="space-y-3"><h2 className="flex items-center gap-2 text-lg font-semibold"><Archive className="h-5 w-5"/>Archived records <span className="text-xs font-normal text-muted-foreground">({archives.length})</span></h2>{archives.length===0?<p className="rounded-lg border p-4 text-sm text-muted-foreground">No archived records.</p>:<div className="space-y-2">{archives.map(a=><div key={`${a.record_type}-${a.record_id}`} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3 text-sm"><div><span className="font-medium">{nameOf(a.record_type,a.record_id)}</span><p className="text-xs text-muted-foreground">{a.record_type} #{a.record_id} · Archived {new Date(a.archived_at).toLocaleDateString('en-GB')}</p></div><button className="rounded-md border px-3 py-2 text-sm hover:bg-accent" disabled={busy} onClick={()=>openAction(a.record_type,a.record_id,'RESTORE')}>Restore</button></div>)}</div>}</section>
  {pending&&<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="presentation"><div role="dialog" aria-modal="true" aria-labelledby="lifecycle-confirm-heading" className="w-full max-w-lg space-y-4 rounded-xl border bg-background p-6 shadow-xl"><div className="flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-amber-600"/><h2 id="lifecycle-confirm-heading" className="text-lg font-semibold">Confirm {pending.action.toLowerCase()}</h2></div><p className="text-sm">{pending.name} <strong>(#{pending.id})</strong> · {pending.kind}</p><p className="text-sm text-muted-foreground">{pending.action==='DELETE'?'Permanent deletion cannot be undone. Linked historical data or archived descendants will prevent deletion.':pending.action==='ARCHIVE'?'Archiving removes applicable public visibility but preserves history. Dependencies may prevent the action.':'Restoring will not automatically republish the record.'}</p><div className="rounded-md border bg-muted/30 p-3 text-xs">Audit reason: {reason.trim()}</div><label className="block space-y-1.5 text-sm">Type <strong>{pending.action}</strong> to proceed<input autoFocus value={confirmText} onChange={e=>setConfirmText(e.target.value)} className="block w-full rounded-md border bg-background px-3 py-2"/></label><div className="flex justify-end gap-2"><button className="rounded-md border px-4 py-2 text-sm" disabled={busy} onClick={()=>setPending(null)}>Cancel</button><button className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-40" disabled={busy||confirmText!==pending.action} onClick={()=>void perform()}>{busy?'Working…':`Confirm ${pending.action}`}</button></div></div></div>}
 </div>
}
