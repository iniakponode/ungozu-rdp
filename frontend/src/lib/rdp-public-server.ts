/** Server-side read-only published catalogue. Never uses admin credentials. */
import type { Catalogue } from './rdp-catalogue'

export async function publishedCatalogues(): Promise<Catalogue[]> {
  const base = process.env.BACKEND_URL || 'http://127.0.0.1:8010'
  try {
    const response = await fetch(new URL('/api/v1/rdp/public/catalogue', base), {cache: 'no-store'})
    if (!response.ok) return []
    const result: unknown = await response.json()
    return Array.isArray(result) ? result as Catalogue[] : []
  } catch { return [] }
}
