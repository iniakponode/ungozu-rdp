'use client'
import { formatRdpEventTime, parseRdpEventTimestamp, watInputToUtcIso, eventTimestampToWatInput } from '@/lib/rdp-event-time'
import { useEffect, useRef, useState } from 'react'
import { createRDPEvent, createRDPResource, deleteRDPEvent, deleteRDPResource, getRDPEvents, getRDPResources, updateRDPEvent, updateRDPResource, type RDPEventAdmin, type RDPResourceAdmin } from '@/lib/rdp-admin-api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { fetchBuilder, type Cohort } from '@/lib/rdp-builder-api'
import { AdminHelpLink } from '@/components/rdp/help-link'
import { ApiErrorAlert } from '@/components/ui/api-error-alert'
import { userErrorMessage } from '@/lib/api-errors'

type EventEditorState = {
 record: RDPEventAdmin
 startsAt: string
 endsAt: string
}

export default function RDPContentPage(){
 const [events,setEvents]=useState<RDPEventAdmin[]>([]),[resources,setResources]=useState<RDPResourceAdmin[]>([]),[cohorts,setCohorts]=useState<Cohort[]>([]),[cohortId,setCohortId]=useState<number|null>(null),[loadError,setLoadError]=useState(''),[event,setEvent]=useState({title:'',event_type:'masterclass',starts_at:'',ends_at:'',delivery_mode:'online',meeting_url:'',description:'',is_published:false}),[resource,setResource]=useState({title:'',resource_type:'document',url:'',description:'',month_number:'',sort_order:'0',is_published:false})
 const selectedCohortRef=useRef<number|null>(null)

 const load=async(id:number)=>{
  const [nextEvents,nextResources]=await Promise.all([
   getRDPEvents(id),
   getRDPResources(id),
  ])

  if(selectedCohortRef.current!==id)return

  setEvents(nextEvents)
  setResources(nextResources)
 }
 useEffect(()=>{fetchBuilder().then(d=>{setCohorts(d.cohorts)}).catch(e=>setLoadError(userErrorMessage(e,'Could not load cohorts')))},[])
 useEffect(()=>{
  if(cohortId===null)return

  let cancelled=false

  Promise.all([getRDPEvents(cohortId),getRDPResources(cohortId)])
    .then(([events,resources])=>{
      if(cancelled)return
      setEvents(events)
      setResources(resources)
      setLoadError('')
    })
    .catch(error=>{
      if(!cancelled){
        setLoadError(userErrorMessage(error,'Failed to load RDP content'))
      }
    })

  return ()=>{cancelled=true}
},[cohortId])
 const addEvent=async()=>{
  if(cohortId===null)return

  const startsAt=watInputToUtcIso(event.starts_at)
  const endsAt=event.ends_at?watInputToUtcIso(event.ends_at):null

  if(!startsAt){
   toast.error('Enter a valid event start time in WAT.')
   return
  }

  if(event.ends_at && !endsAt){
   toast.error('Enter a valid event end time in WAT.')
   return
  }

  if(endsAt && new Date(endsAt).getTime()<=new Date(startsAt).getTime()){
   toast.error('The event end time must be later than the start time.')
   return
  }

  try{
   await createRDPEvent(cohortId,{
    title:event.title,
    event_type:event.event_type,
    starts_at:startsAt,
    ends_at:endsAt,
    delivery_mode:event.delivery_mode||null,
    meeting_url:event.meeting_url||null,
    description:event.description||null,
    is_published:event.is_published,
   })

   toast.success('Event created')
   setEvent({
    ...event,
    title:'',
    starts_at:'',
    ends_at:'',
    meeting_url:'',
    description:'',
    is_published:false,
   })
   await load(cohortId)
  }catch(error){
   toast.error(userErrorMessage(error,'Could not create event'))
  }
 }
 const addResource=async()=>{if(cohortId===null)return;try{await createRDPResource(cohortId,{title:resource.title,resource_type:resource.resource_type,url:resource.url||null,description:resource.description||null,month_number:resource.month_number?Number(resource.month_number):null,sort_order:Number(resource.sort_order)||0,is_published:resource.is_published});toast.success('Resource created');setResource({...resource,title:'',url:'',description:'',month_number:''});await load(cohortId)}catch(e){toast.error(userErrorMessage(e,'Could not create resource'))}}

 const [editingEvent,setEditingEvent]=useState<EventEditorState|null>(null)
 const [eventSaving,setEventSaving]=useState(false)
 const [editingResource,setEditingResource]=useState<RDPResourceAdmin|null>(null)
 const [resourceSaving,setResourceSaving]=useState(false)

 const [publicationBusy,setPublicationBusy]=useState<string|null>(null)

 const toggleEventPublication=async(item:RDPEventAdmin)=>{
  if(cohortId===null || item.cohort_id!==cohortId)return

  const startsAt=parseRdpEventTimestamp(item.starts_at)
  const endsAt=item.ends_at?parseRdpEventTimestamp(item.ends_at):null

  if(!startsAt || (item.ends_at && !endsAt)){
   toast.error('This event has an invalid date. Edit its dates before publishing.')
   return
  }

  const key=`event-${item.id}`
  setPublicationBusy(key)

  try{
   await updateRDPEvent(cohortId,item.id,{
    title:item.title,
    event_type:item.event_type,
    starts_at:startsAt.toISOString(),
    ends_at:endsAt?.toISOString()??null,
    delivery_mode:item.delivery_mode??null,
    meeting_url:item.meeting_url??null,
    description:item.description??null,
    is_published:!item.is_published,
   })
   if(selectedCohortRef.current===cohortId)toast.success(item.is_published?'Event unpublished':'Event published')
   await load(cohortId)
  }catch(error){
   if(selectedCohortRef.current===cohortId)toast.error(userErrorMessage(error,'Could not update event publication'))
  }finally{
   setPublicationBusy(null)
  }
 }

 const beginEventEdit=(item:RDPEventAdmin)=>{
  if(cohortId===null || item.cohort_id!==cohortId)return

  const startsAt=eventTimestampToWatInput(item.starts_at)
  const endsAt=item.ends_at
   ?eventTimestampToWatInput(item.ends_at)
   :''

  if(!startsAt || (item.ends_at && !endsAt)){
   toast.error('Cannot edit this event: invalid stored date.')
   return
  }

  setEditingEvent({
   record:{...item},
   startsAt,
   endsAt:endsAt??'',
  })
 }

 const saveEventEdit=async()=>{
  const edit=editingEvent
  const selectedId=cohortId

  if(!edit || selectedId===null ||
     edit.record.cohort_id!==selectedId)return

  if(eventSaving || publicationBusy!==null)return

  const startsAt=watInputToUtcIso(edit.startsAt)
  const endsAt=edit.endsAt?watInputToUtcIso(edit.endsAt):null

  if(!startsAt || (edit.endsAt && !endsAt)){
   toast.error('Enter valid event dates in WAT.')
   return
  }

  if(endsAt && new Date(endsAt).getTime()<=new Date(startsAt).getTime()){
   toast.error('Event end time must be later than start time.')
   return
  }

  if(edit.record.title.trim().length<2){
   toast.error('Event title must contain at least two characters.')
   return
  }

  setEventSaving(true)

  try{
   await updateRDPEvent(selectedId,edit.record.id,{
    title:edit.record.title.trim(),
    event_type:edit.record.event_type,
    starts_at:startsAt,
    ends_at:endsAt,
    delivery_mode:edit.record.delivery_mode??null,
    meeting_url:edit.record.meeting_url??null,
    description:edit.record.description??null,
    is_published:edit.record.is_published,
   })

   if(selectedCohortRef.current===selectedId){
    setEditingEvent(null)
    await load(selectedId)
    toast.success('Event changes saved')
   }
  }catch(error){
   if(selectedCohortRef.current===selectedId){
    toast.error(userErrorMessage(error,'Could not save event changes'))
   }
  }finally{
   setEventSaving(false)
  }
 }

 const saveResourceEdit=async()=>{
  const item=editingResource
  const selectedId=cohortId

  if(!item || selectedId===null || item.cohort_id!==selectedId)return
  if(resourceSaving || publicationBusy!==null)return

  if(item.title.trim().length<2){
   toast.error('Resource title must contain at least two characters.')
   return
  }

  if(item.month_number != null &&
     (!Number.isInteger(item.month_number) ||
      item.month_number < 1 || item.month_number > 12)){
   toast.error('Resource month must be between 1 and 12.')
   return
  }

  if(!Number.isInteger(item.sort_order) ||
     item.sort_order<0 || item.sort_order>32767){
   toast.error('Sort order must be between 0 and 32767.')
   return
  }

  setResourceSaving(true)

  try{
   await updateRDPResource(selectedId,item.id,{
    title:item.title.trim(),
    resource_type:item.resource_type.trim(),
    url:item.url?.trim()||null,
    description:item.description||null,
    month_number:item.month_number,
    sort_order:item.sort_order,
    is_published:item.is_published,
   })

   if(selectedCohortRef.current===selectedId){
    setEditingResource(null)
    await load(selectedId)
    toast.success('Resource changes saved')
   }
  }catch(error){
   if(selectedCohortRef.current===selectedId){
    toast.error(userErrorMessage(error,'Could not save resource changes'))
   }
  }finally{
   setResourceSaving(false)
  }
 }

 const toggleResourcePublication=async(item:RDPResourceAdmin)=>{
  if(cohortId===null || item.cohort_id!==cohortId)return

  const key=`resource-${item.id}`
  setPublicationBusy(key)

  try{
   await updateRDPResource(cohortId,item.id,{
    title:item.title,
    resource_type:item.resource_type,
    url:item.url??null,
    description:item.description??null,
    month_number:item.month_number??null,
    sort_order:item.sort_order,
    is_published:!item.is_published,
   })
   if(selectedCohortRef.current===cohortId)toast.success(item.is_published?'Resource unpublished':'Resource published')
   await load(cohortId)
  }catch(error){
   if(selectedCohortRef.current===cohortId)toast.error(userErrorMessage(error,'Could not update resource publication'))
  }finally{
   setPublicationBusy(null)
  }
 }

 const deleteBusyRef=useRef(false)
 const [deletingKey,setDeletingKey]=useState<string|null>(null)

 const deleteContent=async(
  kind:'event'|'resource',
  item:RDPEventAdmin|RDPResourceAdmin
 )=>{
  const selectedId=cohortId

  if(selectedId===null ||
     selectedCohortRef.current!==selectedId ||
     item.cohort_id!==selectedId ||
     deleteBusyRef.current)return

  if(!confirm(`Delete this ${kind}?`))return

  if(selectedCohortRef.current!==selectedId)return

  deleteBusyRef.current=true
  setDeletingKey(`${kind}-${item.id}`)

  let deleted=false

  try{
   if(kind==='event'){
    await deleteRDPEvent(selectedId,item.id)
   }else{
    await deleteRDPResource(selectedId,item.id)
   }

   deleted=true

   if(selectedCohortRef.current===selectedId){
    await load(selectedId)
    toast.success(`${kind==='event'?'Event':'Resource'} deleted`)
   }
  }catch(error){
   if(selectedCohortRef.current===selectedId){
    toast.error(userErrorMessage(
     error,
     deleted
      ? 'Deleted, but could not refresh content'
      : `Could not delete ${kind}`
    ))
   }
  }finally{
   deleteBusyRef.current=false
   setDeletingKey(null)
  }
 }

 return <div className="space-y-8"><div><h1 className="text-2xl font-bold">RDP programme content</h1><AdminHelpLink topic="content"/><p className="text-sm text-muted-foreground">Publish events and participant resources to the authenticated programme portal.</p></div>
 <ApiErrorAlert message={loadError}/><div className="rounded-lg border bg-card p-4 space-y-2"><label className="block text-sm font-medium" htmlFor="content-cohort">Manage content for cohort</label><select id="content-cohort" className="w-full rounded-md border bg-background p-2 text-sm" value={cohortId??""} onChange={e=>{
      setEditingEvent(null)
      setEditingResource(null)
      setEvents([])
      setResources([])
      setLoadError('')
      selectedCohortRef.current=e.target.value?Number(e.target.value):null
      setCohortId(selectedCohortRef.current)
    }}><option value="">Choose cohort</option>{cohorts.map(c=><option value={c.id} key={c.id}>{c.label}{c.is_published?"":" (unpublished)"}</option>)}</select>{cohortId===null&&<p className="text-sm text-muted-foreground">Choose or create a cohort before managing content.</p>}</div>{cohortId!==null&&<><div className="grid gap-6 xl:grid-cols-2"><Card><CardHeader><CardTitle>Create event</CardTitle></CardHeader><CardContent className="space-y-3"><div><Label>Title</Label><Input value={event.title} onChange={e=>setEvent(x=>({...x,title:e.target.value}))}/></div><div className="grid gap-3 sm:grid-cols-2"><div><Label>Type</Label><Input value={event.event_type} onChange={e=>setEvent(x=>({...x,event_type:e.target.value}))}/></div><div><Label>Delivery mode</Label><Input value={event.delivery_mode} onChange={e=>setEvent(x=>({...x,delivery_mode:e.target.value}))}/></div><div><Label>Starts (WAT, UTC+1)</Label><Input type="datetime-local" value={event.starts_at} onChange={e=>setEvent(x=>({...x,starts_at:e.target.value}))}/></div><div><Label>Ends (WAT, optional)</Label><Input type="datetime-local" value={event.ends_at} onChange={e=>setEvent(x=>({...x,ends_at:e.target.value}))}/></div></div><div><Label>Meeting URL</Label><Input value={event.meeting_url} onChange={e=>setEvent(x=>({...x,meeting_url:e.target.value}))}/></div><div><Label>Description</Label><Textarea value={event.description} onChange={e=>setEvent(x=>({...x,description:e.target.value}))}/></div><label className="flex gap-2 text-sm"><input type="checkbox" checked={event.is_published} onChange={e=>setEvent(x=>({...x,is_published:e.target.checked}))}/>Publish to participants</label><Button disabled={!event.title||!event.starts_at} onClick={addEvent}>Create event</Button></CardContent></Card>
 <Card><CardHeader><CardTitle>Create resource</CardTitle></CardHeader><CardContent className="space-y-3"><div><Label>Title</Label><Input value={resource.title} onChange={e=>setResource(x=>({...x,title:e.target.value}))}/></div><div className="grid gap-3 sm:grid-cols-2"><div><Label>Type</Label><Input value={resource.resource_type} onChange={e=>setResource(x=>({...x,resource_type:e.target.value}))}/></div><div><Label>Month (optional)</Label><Input type="number" min={1} max={12} value={resource.month_number} onChange={e=>setResource(x=>({...x,month_number:e.target.value}))}/></div></div><div><Label>URL</Label><Input value={resource.url} onChange={e=>setResource(x=>({...x,url:e.target.value}))}/></div><div><Label>Description</Label><Textarea value={resource.description} onChange={e=>setResource(x=>({...x,description:e.target.value}))}/></div><label className="flex gap-2 text-sm"><input type="checkbox" checked={resource.is_published} onChange={e=>setResource(x=>({...x,is_published:e.target.checked}))}/>Publish to participants</label><Button disabled={!resource.title} onClick={addResource}>Create resource</Button></CardContent></Card></div>
 {editingEvent!==null&&
  cohortId===editingEvent.record.cohort_id&&
 <Card>
  <CardHeader>
   <CardTitle>Edit event</CardTitle>
   <p className="text-sm text-muted-foreground">
    All dates are West Africa Time (UTC+1).
    Saving preserves the current publication status.
   </p>
  </CardHeader>
  <CardContent className="space-y-3">
   <div>
    <Label>Title</Label>
    <Input value={editingEvent.record.title}
     onChange={e=>setEditingEvent(x=>x?{
      ...x,record:{...x.record,title:e.target.value}
     }:x)}/>
   </div>
   <div className="grid gap-3 sm:grid-cols-2">
    <div>
     <Label>Event type</Label>
     <Input value={editingEvent.record.event_type}
      onChange={e=>setEditingEvent(x=>x?{
       ...x,record:{...x.record,event_type:e.target.value}
      }:x)}/>
    </div>
    <div>
     <Label>Delivery mode</Label>
     <Input value={editingEvent.record.delivery_mode??''}
      onChange={e=>setEditingEvent(x=>x?{
       ...x,record:{...x.record,delivery_mode:e.target.value}
      }:x)}/>
    </div>
    <div>
     <Label>Starts (WAT)</Label>
     <Input type="datetime-local" value={editingEvent.startsAt}
      onChange={e=>setEditingEvent(x=>x?{
       ...x,startsAt:e.target.value
      }:x)}/>
    </div>
    <div>
     <Label>Ends (WAT, optional)</Label>
     <Input type="datetime-local" value={editingEvent.endsAt}
      onChange={e=>setEditingEvent(x=>x?{
       ...x,endsAt:e.target.value
      }:x)}/>
    </div>
   </div>
   <div>
    <Label>Meeting URL</Label>
    <Input value={editingEvent.record.meeting_url??''}
     onChange={e=>setEditingEvent(x=>x?{
      ...x,record:{...x.record,meeting_url:e.target.value}
     }:x)}/>
   </div>
   <div>
    <Label>Description</Label>
    <Textarea value={editingEvent.record.description??''}
     onChange={e=>setEditingEvent(x=>x?{
      ...x,record:{...x.record,description:e.target.value}
     }:x)}/>
   </div>
   <p className="text-sm">
    Publication: {editingEvent.record.is_published?'Published':'Draft'}
   </p>
   <div className="flex gap-2">
    <Button disabled={eventSaving||publicationBusy!==null}
     onClick={saveEventEdit}>
     {eventSaving?'Saving...':'Save changes'}
    </Button>
    <Button variant="outline" disabled={eventSaving}
     onClick={()=>setEditingEvent(null)}>
     Cancel
    </Button>
   </div>
  </CardContent>
 </Card>}

 {editingResource!==null&&cohortId===editingResource.cohort_id&&
 <Card>
  <CardHeader>
   <CardTitle>Edit resource</CardTitle>
   <p className="text-sm text-muted-foreground">
    Changes will retain the resource&apos;s current publication status.
   </p>
  </CardHeader>
  <CardContent className="space-y-3">
   <div>
    <Label>Title</Label>
    <Input value={editingResource.title}
     onChange={e=>setEditingResource(x=>x?{...x,title:e.target.value}:x)}/>
   </div>
   <div>
    <Label>Resource type</Label>
    <Input value={editingResource.resource_type}
     onChange={e=>setEditingResource(x=>x?{...x,resource_type:e.target.value}:x)}/>
   </div>
   <div>
    <Label>URL</Label>
    <Input value={editingResource.url??''}
     onChange={e=>setEditingResource(x=>x?{...x,url:e.target.value}:x)}/>
   </div>
   <div>
    <Label>Description</Label>
    <Textarea value={editingResource.description??''}
     onChange={e=>setEditingResource(x=>x?{...x,description:e.target.value}:x)}/>
   </div>
   <div className="grid gap-3 sm:grid-cols-2">
    <div>
     <Label>Month (optional)</Label>
     <Input type="number" min={1} max={12}
      value={editingResource.month_number??''}
      onChange={e=>setEditingResource(x=>x?{
       ...x,
       month_number:e.target.value===''?null:Number(e.target.value),
      }:x)}/>
    </div>
    <div>
     <Label>Sort order</Label>
     <Input type="number" min={0} max={32767}
      value={editingResource.sort_order}
      onChange={e=>setEditingResource(x=>x?{
       ...x,sort_order:Number(e.target.value),
      }:x)}/>
    </div>
   </div>
   <p className="text-sm">
    Publication status: {editingResource.is_published?'Published':'Draft'}
   </p>
   <div className="flex gap-2">
    <Button disabled={resourceSaving||publicationBusy!==null}
     onClick={saveResourceEdit}>
     {resourceSaving?'Saving...':'Save changes'}
    </Button>
    <Button variant="outline" disabled={resourceSaving}
     onClick={()=>setEditingResource(null)}>
     Cancel
    </Button>
   </div>
  </CardContent>
 </Card>}

 <div className="grid gap-6 xl:grid-cols-2"><Card><CardHeader><CardTitle>Events</CardTitle></CardHeader><CardContent className="space-y-3">{events.map(e=><div key={e.id} className="rounded-md border p-3"><div className="flex items-start justify-between gap-3"><div><p className="font-medium">{e.title}</p><p className="text-xs text-muted-foreground">{formatRdpEventTime(e.starts_at)} · {e.event_type}</p></div><Badge variant="outline">{e.is_published?'published':'hidden'}</Badge></div><Button size="sm" variant="outline" className="mt-3 mr-2" disabled={eventSaving||publicationBusy!==null} onClick={()=>beginEventEdit(e)}>Edit</Button><Button size="sm" variant="outline" className="mt-3 mr-2" disabled={publicationBusy!==null} onClick={()=>toggleEventPublication(e)}>{publicationBusy===`event-${e.id}`?'Saving...':e.is_published?'Unpublish':'Publish'}</Button><Button size="sm" variant="destructive" className="mt-3" disabled={deletingKey!==null||eventSaving||resourceSaving||publicationBusy!==null} onClick={()=>void deleteContent('event',e)}>Delete</Button></div>)}{!events.length&&<p className="text-sm text-muted-foreground">No events yet.</p>}</CardContent></Card>
 <Card><CardHeader><CardTitle>Resources</CardTitle></CardHeader><CardContent className="space-y-3">{resources.map(r=><div key={r.id} className="rounded-md border p-3"><div className="flex items-start justify-between gap-3"><div><p className="font-medium">{r.title}</p><p className="text-xs text-muted-foreground">{r.month_number?`Month ${r.month_number} · `:''}{r.resource_type}</p></div><Badge variant="outline">{r.is_published?'published':'hidden'}</Badge></div>{r.url&&<p className="mt-1 truncate text-xs text-muted-foreground">{r.url}</p>}<Button size="sm" variant="outline" className="mt-3 mr-2" disabled={publicationBusy!==null} onClick={()=>toggleResourcePublication(r)}>{publicationBusy===`resource-${r.id}`?'Saving...':r.is_published?'Unpublish':'Publish'}</Button><Button size="sm" variant="outline" className="mt-3 mr-2"
 disabled={resourceSaving||publicationBusy!==null}
 onClick={()=>setEditingResource({...r})}>Edit</Button><Button size="sm" variant="destructive" className="mt-3" disabled={deletingKey!==null||eventSaving||resourceSaving||publicationBusy!==null} onClick={()=>void deleteContent('resource',r)}>Delete</Button></div>)}{!resources.length&&<p className="text-sm text-muted-foreground">No resources yet.</p>}</CardContent></Card></div>
 </>}
 </div>
}
