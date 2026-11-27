'use client'

import { useState } from 'react'
import { BookOpen, Link2 } from 'lucide-react'
import RDPContentPage from '@/app/admin/content/page'
import LearningResourcesAdminPage from '@/app/admin/learning-resources/page'

type MaterialTab = 'references' | 'documents'

/**
 * A single administrator entry point for the existing, independently
 * authorised learning-material workflows. They deliberately retain their
 * separate cohort and programme-version publication boundaries.
 */
export default function LearningMaterialsPage() {
  const [tab, setTab] = useState<MaterialTab>('references')
  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Learning Materials</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Manage cohort-specific links and references alongside protected
          curriculum documents. Each type retains its own access rules.
        </p>
      </div>
      <div role="tablist" aria-label="Learning material type" className="flex flex-wrap gap-2 rounded-lg border p-2">
        <button type="button" role="tab" id="learning-links-tab"
          aria-selected={tab === 'references'} aria-controls="learning-links-panel"
          onClick={() => setTab('references')}
          className={`inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium ${tab === 'references' ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'}`}>
          <Link2 className="h-4 w-4" /> Cohort links &amp; references
        </button>
        <button type="button" role="tab" id="learning-documents-tab"
          aria-selected={tab === 'documents'} aria-controls="learning-documents-panel"
          onClick={() => setTab('documents')}
          className={`inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium ${tab === 'documents' ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'}`}>
          <BookOpen className="h-4 w-4" /> Protected learning documents
        </button>
      </div>
      {tab === 'references' ? (
        <div id="learning-links-panel" role="tabpanel" aria-labelledby="learning-links-tab">
          <p className="mb-4 text-sm text-muted-foreground">
            Cohort-scoped material. Select a cohort, then use the Resources form below.
            The same page also provides programme events.
          </p>
          <RDPContentPage />
        </div>
      ) : (
        <div id="learning-documents-panel" role="tabpanel" aria-labelledby="learning-documents-tab">
          <p className="mb-4 text-sm text-muted-foreground">
            Programme-version documents. Upload DOCX learning materials against a
            curriculum module; staff-only documents remain hidden from participants.
          </p>
          <LearningResourcesAdminPage />
        </div>
      )}
    </section>
  )
}
