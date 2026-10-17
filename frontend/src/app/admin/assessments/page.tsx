'use client'
import { useEffect, useState } from 'react'
import { fetchBuilder, type Version } from '@/lib/rdp-builder-api'
import { createCriterion, editCriterion, listCriteria, type Criterion, type CriterionInput } from '@/lib/rdp-completion-api'
import { Card,CardContent,CardHeader,CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { toast } from 'sonner'
import { AdminHelpLink } from '@/components/rdp/help-link'
import { ApiErrorAlert } from '@/components/ui/api-error-alert'
import { userErrorMessage } from '@/lib/api-errors'
const empty:CriterionInput={code:'',title:'',description:'',category:'research',max_score:100,pass_score:60,required:true,sort_order:0}
export default function AssessmentRubrics(){
 const [versions,setVersions]=useState<Version[]>([]),[selected,setSelected]=useState<number|null>(null),[criteria,setCriteria]=useState<Criterion[]>([]),[draft,setDraft]=useState<CriterionInput>(empty),[editing,setEditing]=useState<number|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const current=versions.find(v=>v.id===selected)
 async function refresh(id:number){const rows=await listCriteria(id);setCriteria(rows)}
 // Ignore late initialisation responses, including React Strict Mode effect replays.
 useEffect(()=>{
  let active=true
  fetchBuilder().then(d=>{
   if(!active)return
   setVersions(d.versions)
   setSelected(previous=>previous??(d.versions[0]?.id??null))
  }).catch(e=>{if(active)setError(userErrorMessage(e,'Could not load assessment rubrics'))})
  return ()=>{active=false}
 },[])
 // Ignore stale rubric responses when the administrator switches versions quickly.
 useEffect(()=>{
  let active=true
  setCriteria([])
  if(selected!==null){
   listCriteria(selected).then(rows=>{if(active)setCriteria(rows)})
    .catch(e=>{if(active)setError(userErrorMessage(e,'Could not load assessment rubrics'))})
  }
  return ()=>{active=false}
 },[selected])
 function edit(c:Criterion){setEditing(c.id);setDraft({code:c.code,title:c.title,description:c.description,category:c.category,max_score:c.max_score,pass_score:c.pass_score,required:c.required,sort_order:c.sort_order})}
 async function save(){if(selected===null)return;setBusy(true);try{if(editing!==null)await editCriterion(editing,draft);else await createCriterion(selected,draft);await refresh(selected);setEditing(null);setDraft(empty);toast.success('Assessment criterion saved')}catch(e){toast.error(userErrorMessage(e,'Could not save criterion'))}finally{setBusy(false)}}
 return <div className="space-y-6"><div><h1 className="text-2xl font-bold">Assessment rubrics</h1><AdminHelpLink topic="assessments"/><p className="mt-2 text-sm text-muted-foreground">Define evidence and passing scores for each programme version while it is still a draft. Published versions retain their criteria permanently; clone a version to make changes.</p></div>
 <ApiErrorAlert message={error}/>
 <Card><CardHeader><CardTitle>Programme version</CardTitle></CardHeader><CardContent><Label htmlFor="rubric-version">Select version</Label><select id="rubric-version" className="mt-2 w-full rounded-md border bg-background p-3 text-sm" value={selected??''} onChange={e=>{setSelected(Number(e.target.value));setEditing(null);setDraft(empty)}}>{versions.map(v=><option key={v.id} value={v.id}>{v.title} · v{v.version_number} · {v.duration_value} {v.duration_unit} · {v.status}</option>)}</select></CardContent></Card>
 {current&&<Card><CardHeader><CardTitle>Criteria for {current.title}</CardTitle></CardHeader><CardContent className="space-y-3">{criteria.length?criteria.map(c=><div key={c.id} className="flex items-start justify-between gap-4 rounded border p-4"><div><p className="font-semibold">{c.title} {c.required?'(required)':'(optional)'}</p><p className="text-sm text-muted-foreground">{c.code} · {c.category} · Pass {c.pass_score}/{c.max_score}</p><p className="mt-1 whitespace-pre-wrap text-sm">{c.description}</p></div>{current.status==='draft'&&<Button size="sm" variant="outline" onClick={()=>edit(c)}>Edit</Button>}</div>):<p className="text-sm text-muted-foreground">No assessment criteria yet. Add at least one required criterion before admitting participants you intend to certify.</p>}</CardContent></Card>}
 {current?.status==='draft'&&<Card><CardHeader><CardTitle>{editing===null?'Add criterion':'Edit criterion'}</CardTitle></CardHeader><CardContent className="space-y-4"><div className="grid gap-4 md:grid-cols-2"><div><Label>Unique code</Label><Input value={draft.code} onChange={e=>setDraft(x=>({...x,code:e.target.value}))} placeholder="research-proposal"/></div><div><Label>Title</Label><Input value={draft.title} onChange={e=>setDraft(x=>({...x,title:e.target.value}))}/></div><div><Label>Category</Label><Input value={draft.category} onChange={e=>setDraft(x=>({...x,category:e.target.value}))}/></div><div><Label>Sort order</Label><Input type="number" min={0} value={draft.sort_order} onChange={e=>setDraft(x=>({...x,sort_order:Number(e.target.value)}))}/></div><div><Label>Maximum score</Label><Input type="number" min={1} max={1000} value={draft.max_score} onChange={e=>setDraft(x=>({...x,max_score:Number(e.target.value)}))}/></div><div><Label>Passing score</Label><Input type="number" min={0} max={draft.max_score} value={draft.pass_score} onChange={e=>setDraft(x=>({...x,pass_score:Number(e.target.value)}))}/></div></div><div><Label>Evidence expectations and criteria</Label><Textarea value={draft.description??''} rows={3} onChange={e=>setDraft(x=>({...x,description:e.target.value}))}/></div><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={draft.required} onChange={e=>setDraft(x=>({...x,required:e.target.checked}))}/>Required for completion</label><div className="flex gap-3"><Button disabled={busy||!draft.code||!draft.title} onClick={save}>{busy?'Saving…':'Save criterion'}</Button>{editing!==null&&<Button variant="outline" onClick={()=>{setEditing(null);setDraft(empty)}}>Cancel edit</Button>}</div></CardContent></Card>}
 {current?.status!=='draft'&&current&&<p className="text-sm text-muted-foreground">This version is published. Its assessment criteria are read-only. Clone the version in Programme Builder to revise requirements for future participants.</p>}</div>
}
