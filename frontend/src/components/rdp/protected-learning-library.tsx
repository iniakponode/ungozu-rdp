'use client'
import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { userErrorMessage } from '@/lib/api-errors'
import { downloadResource, participantResources, type LearningResource } from '@/lib/rdp-learning-resources-api'

export function ProtectedLearningLibrary({ versionId }: { versionId: number | null }) {
  const [result, setResult] = useState<{ versionId: number; items: LearningResource[]; error: string } | null>(null)
  const [downloadError, setDownloadError] = useState('')
  const items = result?.versionId === versionId ? result.items : []
  const error = (result?.versionId === versionId ? result.error : '') || downloadError
  const loading = Boolean(versionId) && result?.versionId !== versionId
  useEffect(() => {
    if (!versionId) return
    let active = true
    participantResources(versionId)
      .then(data => { if (active) setResult({ versionId, items: data, error: '' }) })
      .catch(e => { if (active) setResult({ versionId, items: [], error: userErrorMessage(e, 'Unable to load protected learning documents') }) })
    return () => { active = false }
  }, [versionId])
  async function download(item: LearningResource) {
    try { await downloadResource(item.id, 'mine', item.original_filename) }
    catch(e) { setDownloadError(userErrorMessage(e, 'Document download failed')) }
  }
  return <Card><CardHeader><CardTitle>Protected DOCX learning documents</CardTitle><p className="text-sm text-muted-foreground">Only published materials assigned to your enrolled programme version are shown.</p></CardHeader><CardContent className="space-y-3">
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    {!versionId && <p className="text-sm text-muted-foreground">No version-linked learning documents are available for this enrolment.</p>}
    {loading && <p className="text-sm text-muted-foreground">Loading learning documents…</p>}
    {!loading && !error && !!versionId && items.length===0 && <p className="text-sm text-muted-foreground">No protected documents have been published yet.</p>}
    {items.map(item => <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3"><div><strong className="block">{item.title}</strong><p className="mt-1 text-xs text-muted-foreground">{item.original_filename} · {(item.size_bytes/1024).toFixed(0)} KiB</p></div><Button variant="outline" size="sm" onClick={()=>void download(item)}>Download DOCX</Button></div>)}
  </CardContent></Card>
}
