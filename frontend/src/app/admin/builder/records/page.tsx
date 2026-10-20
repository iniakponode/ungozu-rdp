'use client'
import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { fetchBuilder, type BuilderData } from '@/lib/rdp-builder-api'
import { userErrorMessage } from '@/lib/api-errors'

type Kind = 'programmes'|'versions'|'cohorts'|'criteria'
type Criterion = {id:number;programme_version_id:number;code:string;title:string;required:boolean}
type Archived = {record_type:Kind;record_id:number;archived_at:string;previous_status:string|null}
const initial:BuilderData = {programmes:[],versions:[],cohorts:[],modules:[],items:[],packages:[],entitlements:[],fee_plans:[],installments:[]}
export default function RecordLifecyclePage(){
 const [data,setData]=useState<BuilderData>(initial)
 const [archives,setArchives]=useState<Archived[]>([])
 const [criteria,setCriteria]=useState<Criterion[]>([])
 const [selected,setSelected]=useState<Kind>('cohorts')
 const [reason,setReason]=useState('')
 const [busy,setBusy]=useState(false)
 const [error,setError]=useState('')
 const [message,setMessage]=useState('')
 const refresh=useCallback(async()=>{
   const [builder,a,c]=await Promise.all([fetchBuilder(),fetch('/api/rdp-admin/builder/records/archives',{cache:'no-store'}),fetch('/api/rdp-admin/builder/records/criteria',{cache:'no-store'})])
   if(!a.ok||!c.ok)throw Error('Could not fetch lifecycle records')
   setData(builder);setArchives(await a.json() as Archived[]);setCriteria(await c.json() as Criterion[])
 },[])
 useEffect(()=>{void refresh().catch(e=>setError(userErrorMessage(e,'Unable to load records')))},[refresh])
 const rows = selected==='programmes'?data.programmes:selected==='versions'?data.versions:selected==='cohorts'?data.cohorts:criteria
 async function act(kind:Kind,id:number,action:'DELETE'|'ARCHIVE'|'RESTORE'){
   setError('');setMessage('')
   if(reason.trim().length<5){setError('Enter a reason of at least five characters');return}
   const name=rows.find(x=>x.id===id)
   const answer=window.prompt(`${action} ${kind} #${id}${name ? ` (${ 'title' in name ? name.title : name.name })` : ''}?\nType ${action} to confirm. This action is audited.`)
   if(answer!==action)return
   setBusy(true)
   try{
     const result=await fetch(`/api/rdp-admin/builder/records/${kind}/${id}${action==='ARCHIVE'?'/archive':action==='RESTORE'?'/restore':''}`,
      {method:action==='DELETE'?'DELETE':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reason,confirmation:action})})
     if(!result.ok){const response=await result.json().catch(()=>({detail:'Operation failed'}));throw Error(String(response.detail ?? 'Operation failed'))}
     setMessage(`${action} completed for ${kind} #${id}`);await refresh()
   }catch(e){setError(userErrorMessage(e,'Operation failed'))}finally{setBusy(false)}
 }
 const isArchived=(k:Kind,id:number)=>archives.some(a=>a.record_type===k&&a.record_id===id)
 return <main className="mx-auto max-w-5xl space-y-5 p-6">
  <Link className="underline" href="/admin/builder">← Programme Builder</Link>
  <h1 className="text-2xl font-semibold">Manage draft, archived and historical records</h1>
  <p className="text-sm">Delete is only for unused drafts and their unused configuration. Archived records are retained for historical integrity. Restore does not automatically republish cohorts.</p>
  {error&&<p role="alert" className="text-red-600">{error}</p>}{message&&<p role="status">{message}</p>}
  <label className="block">Reason for action <input className="block w-full rounded border p-2" value={reason} maxLength={500} onChange={e=>setReason(e.target.value)} placeholder="Why is this necessary?" /></label>
  <label className="block">Record type <select className="ml-2 rounded border p-2" value={selected} onChange={e=>setSelected(e.target.value as Kind)}>{(['cohorts','versions','programmes','criteria'] as Kind[]).map(x=><option key={x}>{x}</option>)}</select></label>
  {selected==='criteria'&&<p className="text-sm">Archived criteria remain in historical records. Criteria linked to a cohort or past evaluations cannot be archived.</p>}
  <div className="space-y-3">{rows.map(row=><section key={row.id} className="flex flex-wrap items-center justify-between gap-3 rounded border p-3"><div><strong>#{row.id}: {'title' in row ? row.title : row.name}</strong><p className="text-sm">{'status' in row ? row.status : ''}{isArchived(selected,row.id)?' · Archived':''}</p></div><div className="flex gap-2"><button className="rounded border p-2" disabled={busy||isArchived(selected,row.id)} onClick={()=>void act(selected,row.id,'DELETE')}>Delete unused draft</button><button className="rounded border p-2" disabled={busy||isArchived(selected,row.id)} onClick={()=>void act(selected,row.id,'ARCHIVE')}>Archive</button><button className="rounded border p-2" disabled={busy||!isArchived(selected,row.id)} onClick={()=>void act(selected,row.id,'RESTORE')}>Restore</button></div></section>)}</div>
  <h2 className="text-xl font-semibold">Archived records</h2>
  {archives.length===0?<p>None</p>:<div className="space-y-2">{archives.map(a=><div key={`${a.record_type}-${a.record_id}`} className="flex items-center justify-between rounded border p-2"><span>{a.record_type} #{a.record_id} · {a.archived_at}</span><button className="rounded border p-2" disabled={busy} onClick={()=>void act(a.record_type,a.record_id,'RESTORE')}>Restore</button></div>)}</div>}
 </main>
}
