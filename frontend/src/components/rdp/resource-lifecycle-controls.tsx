'use client'
import { useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { userErrorMessage } from '@/lib/api-errors'
import {
  archiveResource, downloadHistoricalResource, getResourceHistory, replaceResource,
  updateResourceMetadata, type LearningResource, type LearningResourceHistory,
} from '@/lib/rdp-learning-resources-api'

const MAX_FILE_BYTES = 15 * 1024 * 1024
export type LifecycleModule = { id: number; title: string; sequence_number: number }

export function ResourceLifecycleControls({ resource, modules, onChanged }: {
  resource: LearningResource
  modules: LifecycleModule[]
  onChanged: () => Promise<void>
}) {
  const [editing, setEditing] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [history, setHistory] = useState<LearningResourceHistory | null>(null)
  const [title, setTitle] = useState(resource.title)
  const [moduleId, setModuleId] = useState(resource.module_id)
  const [audience, setAudience] = useState<'participant' | 'staff'>(resource.audience)
  const [replacement, setReplacement] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)

  async function run(action: () => Promise<unknown>, confirmation: string) {
    if (!window.confirm(confirmation)) return
    setBusy(true)
    try {
      await action()
      await onChanged()
      toast.success('Document updated')
    } catch (err) {
      toast.error(userErrorMessage(err, 'Document update failed'))
    } finally {
      setBusy(false)
    }
  }

  async function saveMetadata(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    try {
      await updateResourceMetadata(resource.id, { title: title.trim(), module_id: moduleId, audience })
      setEditing(false)
      await onChanged()
      toast.success('Document metadata saved')
    } catch (err) {
      toast.error(userErrorMessage(err, 'Could not update metadata'))
    } finally { setBusy(false) }
  }

  async function viewHistory() {
    if (historyOpen) { setHistoryOpen(false); return }
    setBusy(true)
    try {
      const result = await getResourceHistory(resource.id)
      setHistory(result)
      setHistoryOpen(true)
    } catch (err) { toast.error(userErrorMessage(err, 'Could not load revision history')) }
    finally { setBusy(false) }
  }

  async function downloadRevision(revision: number, filename: string) {
    try { await downloadHistoricalResource(resource.id, revision, filename) }
    catch (err) { toast.error(userErrorMessage(err, 'Historical download failed')) }
  }

  return <div className="w-full space-y-3 border-t pt-3">
    <div className="flex flex-wrap gap-2">
      <Button size="sm" variant="outline" disabled={busy} onClick={() => {
        if (!editing) { setTitle(resource.title); setModuleId(resource.module_id); setAudience(resource.audience) }
        setEditing(!editing)
      }}>{editing ? 'Cancel edit' : 'Edit metadata'}</Button>
      <Button size="sm" variant="outline" disabled={busy} onClick={() => void viewHistory()}>
        {historyOpen ? 'Hide history' : `Revision history (current v${resource.file_revision})`}
      </Button>
      <Button size="sm" variant="outline" disabled={busy} onClick={() => void run(
        () => archiveResource(resource.id, !resource.is_archived),
        resource.is_archived
          ? 'Restore this document as an unpublished draft?'
          : 'Archive and unpublish this document? Participants will immediately lose access.',
      )}>{resource.is_archived ? 'Restore draft' : 'Archive document'}</Button>
    </div>

    {editing && <form onSubmit={(e) => void saveMetadata(e)} className="grid gap-3 rounded-md bg-muted/30 p-3 sm:grid-cols-2">
      <div className="space-y-1"><Label htmlFor={`doc-title-${resource.id}`}>Title</Label>
        <Input id={`doc-title-${resource.id}`} required minLength={3} maxLength={255} value={title} onChange={e => setTitle(e.target.value)}/></div>
      <div className="space-y-1"><Label htmlFor={`doc-module-${resource.id}`}>Curriculum module</Label>
        <select id={`doc-module-${resource.id}`} className="w-full rounded-md border bg-background p-2 text-sm" value={moduleId} onChange={e => setModuleId(Number(e.target.value))} required>
          {modules.map(module => <option value={module.id} key={module.id}>{module.sequence_number}. {module.title}</option>)}
        </select></div>
      <div className="space-y-1"><Label htmlFor={`doc-audience-${resource.id}`}>Audience</Label>
        <select id={`doc-audience-${resource.id}`} className="w-full rounded-md border bg-background p-2 text-sm" value={audience} onChange={e => setAudience(e.target.value as 'participant' | 'staff')}>
          <option value="participant">Participant</option><option value="staff">Staff only</option>
        </select></div>
      <div className="flex items-end"><Button type="submit" disabled={busy || !modules.some(m => m.id === moduleId) || title.trim().length < 3}>Save metadata</Button></div>
    </form>}

    {!resource.is_archived && <div className="flex flex-wrap items-end gap-2 rounded-md bg-muted/30 p-3">
      <div className="min-w-0 flex-1 space-y-1"><Label htmlFor={`doc-replace-${resource.id}`}>Replace DOCX (maximum 15 MiB)</Label>
        <Input id={`doc-replace-${resource.id}`} type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={e => setReplacement(e.target.files?.[0] ?? null)}/></div>
      <Button size="sm" disabled={busy || !replacement || !/\.docx$/i.test(replacement.name) || replacement.size === 0 || replacement.size > MAX_FILE_BYTES}
        onClick={() => { const file = replacement; if (file) void run(async () => {
          await replaceResource(resource.id, file)
          setReplacement(null)
          setHistory(null)
          setHistoryOpen(false)
          const input = document.getElementById(`doc-replace-${resource.id}`) as HTMLInputElement | null
          if (input) input.value = ''
        }, 'Replace this DOCX? The existing version will remain in administrator history. The new version will be unpublished until explicitly published.') }}>
        Replace (save previous revision)
      </Button>
    </div>}

    {historyOpen && history && <section aria-label={`History for ${resource.title}`} className="space-y-2 rounded-md border p-3">
      <p className="text-sm font-semibold">Current revision: {history.current_revision}</p>
      {history.versions.length === 0 && <p className="text-sm text-muted-foreground">No previous revisions.</p>}
      {history.versions.map(version => <div key={version.revision_number} className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <span>v{version.revision_number}: {version.original_filename} ({(version.size_bytes / 1024).toFixed(0)} KiB)</span>
        <Button size="sm" variant="outline" onClick={() => void downloadRevision(version.revision_number, version.original_filename)}>Download historical DOCX</Button>
      </div>)}
      <p className="pt-2 text-sm font-semibold">Audit history</p>
      {history.audit.length === 0 && <p className="text-sm text-muted-foreground">No actions recorded yet.</p>}
      <ul className="space-y-1 text-xs text-muted-foreground">
        {history.audit.map((entry, index) => <li key={`${entry.created_at}-${index}`}>{entry.created_at}: {entry.action} (administrator {entry.actor_user_id ?? 'unknown'})</li>)}
      </ul>
    </section>}
  </div>
}
