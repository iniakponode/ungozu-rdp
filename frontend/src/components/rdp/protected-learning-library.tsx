'use client'

import { useEffect, useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { userErrorMessage } from '@/lib/api-errors'
import { downloadResource, participantResources, type LearningResource } from '@/lib/rdp-learning-resources-api'
import type { CatalogueModule } from '@/lib/rdp-catalogue'
import type { PortalDashboard } from '@/lib/rdp-portal-api'

type CohortResource = PortalDashboard['resources'][number]
type Group = { key: string; title: string; documents: LearningResource[]; links: CohortResource[] }

function safeExternalLink(value: string | null | undefined): string | null {
  if (!value) return null
  try {
    const url = new URL(value)
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null
  } catch { return null }
}

export function ProtectedLearningLibrary({
  versionId, modules, cohortResources,
}: {
  versionId: number | null
  modules: CatalogueModule[]
  cohortResources: CohortResource[]
}) {
  const [result, setResult] = useState<{ versionId: number; items: LearningResource[]; error: string } | null>(null)
  const [downloadError, setDownloadError] = useState('')
  const fetchError = result?.versionId === versionId ? result.error : ''
  const loading = versionId !== null && result?.versionId !== versionId

  useEffect(() => {
    if (!versionId) return
    let active = true
    participantResources(versionId)
      .then(items => { if (active) setResult({ versionId, items, error: '' }) })
      .catch(e => { if (active) setResult({ versionId, items: [], error: userErrorMessage(e, 'Unable to load protected learning documents') }) })
    return () => { active = false }
  }, [versionId])

  const groups = useMemo(() => {
    const documents = result?.versionId === versionId ? result.items : []
    const byModule = new Map<number, Group>()
    for (const curriculumModule of [...modules].sort((a, b) => a.sequence_number - b.sequence_number)) {
      byModule.set(curriculumModule.id, {
        key: `module-${curriculumModule.id}`, title: `Module ${curriculumModule.sequence_number}: ${curriculumModule.title}`,
        documents: [], links: [],
      })
    }
    const other: Group = { key: 'other', title: 'General programme materials', documents: [], links: [] }
    for (const item of documents) {
      const group = byModule.get(item.module_id)
      ;(group ?? other).documents.push(item)
    }
    for (const item of cohortResources) {
      const group = item.module_id == null ? null : byModule.get(item.module_id)
      ;(group ?? other).links.push(item)
    }
    const present = [...byModule.values()].filter(group => group.documents.length || group.links.length)
    if (other.documents.length || other.links.length) present.push(other)
    return present
  }, [modules, result, versionId, cohortResources])

  async function download(item: LearningResource) {
    setDownloadError('')
    try { await downloadResource(item.id, 'mine', item.original_filename) }
    catch(e) { setDownloadError(userErrorMessage(e, 'Document download failed')) }
  }

  return <Card>
    <CardHeader>
      <CardTitle>Learning materials by curriculum module</CardTitle>
      <p className="text-sm text-muted-foreground">Protected DOCX documents are available only to eligible participants. Cohort links and references are shown separately within each module.</p>
    </CardHeader>
    <CardContent className="space-y-5">
      {(fetchError || downloadError) && <p role="alert" className="text-sm text-destructive">{fetchError || downloadError}</p>}
      {loading && <p role="status" className="text-sm text-muted-foreground">Loading protected learning documents…</p>}
      {!versionId && <p className="text-sm text-muted-foreground">No version-linked DOCX documents are available for this enrolment. Cohort references, if any, are listed below.</p>}
      {!loading && groups.length === 0 && !fetchError && <p className="text-sm text-muted-foreground">No learning materials have been published for this enrolment.</p>}
      {groups.map(group => <section key={group.key} aria-label={group.title} className="rounded-lg border p-4">
        <h3 className="font-semibold">{group.title}</h3>
        <div className="mt-3 space-y-3">
          {group.documents.map(item => <div key={`document-${item.id}`} className="flex flex-wrap items-start justify-between gap-3 rounded-md border p-3">
            <div className="min-w-0"><p className="text-xs font-medium uppercase text-muted-foreground">Protected DOCX · Revision {item.file_revision ?? 1}</p><strong className="block break-words">{item.title}</strong><p className="mt-1 text-xs text-muted-foreground">{item.original_filename} · {(item.size_bytes / 1024).toFixed(0)} KiB</p></div>
            <Button variant="outline" size="sm" onClick={() => void download(item)}>Download DOCX</Button>
          </div>)}
          {group.links.map(item => {
            const href = safeExternalLink(item.url)
            return <div key={`link-${item.id}`} className="rounded-md border p-3">
              <p className="text-xs font-medium uppercase text-muted-foreground">Cohort reference{item.month_number ? ` · Month ${item.month_number}` : ''} · {item.resource_type}</p>
              <strong className="block break-words">{item.title}</strong>
              {item.description && <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">{item.description}</p>}
              {href && <a href={href} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-sm font-medium text-primary underline">Open reference</a>}
            </div>
          })}
        </div>
      </section>)}
    </CardContent>
  </Card>
}
