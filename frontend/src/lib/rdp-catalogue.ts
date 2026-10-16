/** Public programme catalogue. The backend only exposes published cohort terms. */
export type CatalogueEntitlement = {
  code: string; name: string; quantity: number | null; unit: string | null;
  limit_value: number | null; limit_unit: string | null; period: string | null; description: string | null
}
export type CatalogueItem = { id: number; sequence_number: number; item_type: string; title: string; description: string | null; estimated_minutes: number | null; completion_required: boolean }
export type CatalogueModule = { id: number; sequence_number: number; title: string; summary: string | null; learning_outcomes: string | null; completion_criteria: string | null; is_required: boolean; items: CatalogueItem[] }
export type CataloguePackage = { id: number; code: string; name: string; description: string | null; capacity: number | null; entitlements: CatalogueEntitlement[] }
export type CatalogueFee = { id: number; package_id: number | null; code: string; region: string; name: string; currency: string; total_amount_subunit: number; installment_count: number; description: string | null; installments: Array<{ sequence_number: number; amount_subunit: number; due_offset_days: number; description: string | null }> }
export type Catalogue = {
  cohort: { id: number; name: string; slug: string; label: string; application_open_date: string; application_deadline: string; start_date: string; graduation_date: string; end_date: string; capacity: number; status: string; public_summary: string | null };
  programme: { id: number; name: string; slug: string; category: string | null; description: string | null } | null;
  version: { id: number; version_number: number; title: string; overview: string | null; duration_value: number; duration_unit: string; learning_outcomes: string | null } | null;
  modules: CatalogueModule[]; packages: CataloguePackage[]; fee_plans: CatalogueFee[]; accepting_applications: boolean;
}
export function catalogueTitle(c: Catalogue) { return c.version?.title || c.programme?.name || c.cohort.name }
export function catalogueDuration(c: Catalogue) { return c.version ? `${c.version.duration_value} ${c.version.duration_unit}` : 'Programme duration: see cohort dates' }
export function chooseCatalogue(items: Catalogue[], slug?: string) { return items.find(x => x.cohort.slug === slug) || items.find(x => x.accepting_applications) || items[0] || null }
export function money(subunits: number, currency: string) { return new Intl.NumberFormat('en', {style: 'currency', currency}).format(subunits / 100) }
export function cohortLink(page: string, slug: string) { return `${page}?cohort=${encodeURIComponent(slug)}` }
