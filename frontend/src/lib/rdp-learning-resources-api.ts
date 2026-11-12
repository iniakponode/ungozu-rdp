import { apiErrorFromResponse } from './api-errors'

const base = '/api/rdp-learning-resources'
export type LearningResource = {
  id: number; programme_version_id: number; module_id: number; resource_code: string;
  title: string; audience: 'staff' | 'participant'; original_filename: string;
  size_bytes: number; sha256: string; is_published: boolean
}
async function result<T>(response: Response): Promise<T> {
  if (!response.ok) throw await apiErrorFromResponse(response)
  return response.json() as Promise<T>
}
export async function adminResources(versionId: number) {
  const q = new URLSearchParams({ programme_version_id: String(versionId) })
  return result<LearningResource[]>(await fetch(`${base}/admin?${q}`, { cache: 'no-store' }))
}
export async function participantResources(versionId: number) {
  const q = new URLSearchParams({ programme_version_id: String(versionId) })
  return result<LearningResource[]>(await fetch(`${base}/mine?${q}`, { cache: 'no-store' }))
}
export async function uploadResource(fields: {
  programme_version_id: number; module_id: number; resource_code: string;
  title: string; audience: 'participant' | 'staff'; file: File
}) {
  const q = new URLSearchParams({
    programme_version_id: String(fields.programme_version_id),
    module_id: String(fields.module_id), resource_code: fields.resource_code,
    title: fields.title, audience: fields.audience, original_filename: fields.file.name,
  })
  return result<LearningResource>(await fetch(`${base}/admin/upload?${q}`, {
    method: 'POST', headers: { 'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
    body: fields.file,
  }))
}
export async function setResourcePublished(id: number, is_published: boolean) {
  return result<LearningResource>(await fetch(`${base}/admin/${id}/publish`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_published }),
  }))
}
export async function downloadResource(id: number, audience: 'admin' | 'mine', filename: string) {
  const response = await fetch(`${base}/${audience}/${id}/download`, { cache: 'no-store' })
  if (!response.ok) throw await apiErrorFromResponse(response)
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename.replace(/[\\/]/g, '_')
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1500)
}
