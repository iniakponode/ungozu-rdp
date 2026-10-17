'use client'
import { useMemo, useState } from 'react'
import type { HelpSection } from '@/lib/rdp-admin-help-content'
import { Input } from '@/components/ui/input'
export function AdminHelpSearch({sections}:{sections:HelpSection[]}) {
 const [query,setQuery]=useState('')
 const results=useMemo(()=>{const q=query.trim().toLowerCase();return q?sections.filter(s=>[s.title,...s.blocks.map(b=>b.text??b.rows?.flat().join(' ')??'')].join(' ').toLowerCase().includes(q)):[]},[query,sections])
 return <div className="rounded-xl border bg-card p-4"><label className="block text-sm font-medium" htmlFor="admin-help-search">Search the administrator handbook</label><Input id="admin-help-search" type="search" className="mt-2" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search admissions, rubrics, payment, certificate…"/>{query.trim()&&<div className="mt-3 space-y-2" role="status" aria-live="polite">{results.length===0?<p className="text-sm text-muted-foreground">No sections match. Try a broader term.</p>:results.map(s=><a key={s.id} className="block rounded-md border px-3 py-2 text-sm hover:bg-accent" href={'#'+s.id}>{s.title}</a>)}</div>}</div>
}
