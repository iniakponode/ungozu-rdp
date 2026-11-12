'use client'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { userErrorMessage } from '@/lib/api-errors'
import { fetchBuilder, type BuilderData } from '@/lib/rdp-builder-api'
import { adminResources, downloadResource, setResourcePublished, uploadResource, type LearningResource } from '@/lib/rdp-learning-resources-api'

const MAX = 15 * 1024 * 1024
export default function LearningResourcesAdminPage() {
  const [builder, setBuilder] = useState<BuilderData | null>(null)
  const [versionId, setVersionId] = useState(0)
  const [moduleId, setModuleId] = useState(0)
  const [resources, setResources] = useState<LearningResource[]>([])
  const [code, setCode] = useState('')
  const [title, setTitle] = useState('')
  const [audience, setAudience] = useState<'participant' | 'staff'>('participant')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const versions = builder?.versions ?? []
  const modules = useMemo(() => (builder?.modules ?? []).filter(m => m.programme_version_id === versionId).sort((a,b) => a.sequence_number - b.sequence_number), [builder, versionId])
  useEffect(() => {
    fetchBuilder().then(data => { setBuilder(data); setVersionId(data.versions[0]?.id ?? 0) })
      .catch(e => setError(userErrorMessage(e, 'Unable to load programme versions')))
  }, [])
  // Derive a module within the current version without cascading state updates.
  const effectiveModuleId = modules.some(m => m.id === moduleId) ? moduleId : (modules[0]?.id ?? 0)
  async function refresh() {
    if (!versionId) { setResources([]); return }
    try { setResources(await adminResources(versionId)); setError('') }
    catch (e) { setError(userErrorMessage(e, 'Unable to load learning resources')) }
  }
  useEffect(() => {
    let active = true
    if (versionId) {
      adminResources(versionId)
        .then(rows => { if (active) { setResources(rows); setError('') } })
        .catch(e => { if (active) setError(userErrorMessage(e, 'Unable to load learning resources')) })
    }
    return () => { active = false }
  }, [versionId]) // async fetch prevents effect-synchronous state writes
  async function upload(e: React.FormEvent) {
    e.preventDefault()
    if (!file || !effectiveModuleId || !versionId) return
    if (!/\.docx$/i.test(file.name) || file.size > MAX || file.size === 0) {
      setError('Select a nonempty DOCX file no larger than 15 MiB.'); return
    }
    setBusy(true); setError('')
    try {
      await uploadResource({ programme_version_id: versionId, module_id: effectiveModuleId, resource_code: code.trim(), title: title.trim(), audience, file })
      toast.success('DOCX uploaded as an unpublished draft')
      setCode(''); setTitle(''); setFile(null)
      const input = document.getElementById('resource-file') as HTMLInputElement | null
      if (input) input.value = ''
      await refresh()
    } catch (e) { const message = userErrorMessage(e, 'Upload failed'); setError(message); toast.error(message) }
    finally { setBusy(false) }
  }
  async function publish(resource: LearningResource) {
    setBusy(true)
    try { await setResourcePublished(resource.id, !resource.is_published); await refresh(); toast.success(resource.is_published ? 'Resource unpublished' : 'Resource published') }
    catch (e) { toast.error(userErrorMessage(e, 'Could not update publication')) }
    finally { setBusy(false) }
  }
  async function download(resource: LearningResource) {
    try { await downloadResource(resource.id, 'admin', resource.original_filename) }
    catch (e) { toast.error(userErrorMessage(e, 'Download failed')) }
  }
  return <div className="space-y-6">
    <div><h1 className="text-2xl font-semibold">Protected learning resources</h1><p className="mt-2 text-sm text-muted-foreground">Upload DOCX files to a specific programme version and module. Participant documents remain private until published; staff documents never appear in the participant library.</p></div>
    {error && <p role="alert" className="rounded-md border border-destructive/30 p-3 text-sm text-destructive">{error}</p>}
    <Card><CardHeader><CardTitle>Programme version</CardTitle></CardHeader><CardContent><Label htmlFor="resource-version">Select version</Label><select id="resource-version" className="mt-2 w-full rounded-md border bg-background p-2 text-sm" value={versionId} onChange={e => setVersionId(Number(e.target.value))}>{versions.map(v => <option key={v.id} value={v.id}>{v.title} (v{v.version_number})</option>)}</select></CardContent></Card>
    <Card><CardHeader><CardTitle>Upload DOCX</CardTitle></CardHeader><CardContent><form className="grid gap-4 sm:grid-cols-2" onSubmit={upload}>
      <label className="space-y-1 text-sm"><span>Curriculum module</span><select className="w-full rounded-md border bg-background p-2" value={effectiveModuleId} onChange={e=>setModuleId(Number(e.target.value))} required>{modules.map(m=><option key={m.id} value={m.id}>{m.sequence_number}. {m.title}</option>)}</select></label>
      <div><Label htmlFor="resource-code">Resource code (unique per version)</Label><Input id="resource-code" className="mt-1" required minLength={3} maxLength={100} pattern="[a-z0-9][a-z0-9_-]*" placeholder="module-01-reading" value={code} onChange={e=>setCode(e.target.value)}/></div>
      <div><Label htmlFor="resource-title">Document title</Label><Input id="resource-title" className="mt-1" required minLength={3} maxLength={255} value={title} onChange={e=>setTitle(e.target.value)}/></div>
      <label className="space-y-1 text-sm"><span>Audience</span><select className="w-full rounded-md border bg-background p-2" value={audience} onChange={e=>setAudience(e.target.value as 'participant'|'staff')}><option value="participant">Participant</option><option value="staff">Staff only</option></select></label>
      <div className="sm:col-span-2"><Label htmlFor="resource-file">DOCX file (maximum 15 MiB)</Label><Input id="resource-file" type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" className="mt-1" required onChange={e=>setFile(e.target.files?.[0]??null)}/></div>
      <div className="sm:col-span-2"><Button type="submit" disabled={busy || !modules.length || !file}>{busy?'Working…':'Upload unpublished document'}</Button></div>
    </form></CardContent></Card>
    <Card><CardHeader><CardTitle>Documents in this version ({resources.length})</CardTitle></CardHeader><CardContent className="space-y-3">{resources.length===0 && <p className="text-sm text-muted-foreground">No learning documents have been uploaded for this version.</p>}{resources.map(r => <div key={r.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3"><div className="min-w-0"><strong className="block break-words">{r.title}</strong><p className="text-xs text-muted-foreground">{r.resource_code} · {r.audience} · {r.is_published?'Published':'Draft'} · {(r.size_bytes/1024).toFixed(0)} KiB</p></div><div className="flex gap-2"><Button size="sm" variant="outline" onClick={()=>void download(r)}>Download</Button><Button size="sm" disabled={busy} onClick={()=>void publish(r)}>{r.is_published?'Unpublish':'Publish'}</Button></div></div>)}</CardContent></Card>
  </div>
}
