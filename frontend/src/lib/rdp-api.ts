import { apiErrorFromResponse } from './api-errors'
import type { Catalogue } from './rdp-catalogue'
export type FeePlan = { id:number; code:string; region:string; name:string; currency:string; total_amount_subunit:number; installment_count:number; installment_amount_subunit:number; description?:string|null; is_active:boolean }
export type Cohort = { id:number; name:string; slug:string; label:string; application_open_date:string; application_deadline:string; start_date:string; graduation_date:string; end_date:string; capacity:number; status:string; public_summary?:string|null; fee_plans:FeePlan[] }
export type Invoice = { id:number; sequence:number; amount_subunit:number; currency:string; due_date?:string|null; status:string; paid_at?:string|null }
export type ApplicationStatus = { application_ref:string; full_name:string; cohort_label:string; status:string; scholarship_status?:string|null; fee_plan?:FeePlan|null; acceptance_deadline?:string|null; invoices:Invoice[] }

async function pub<T>(path:string, opts:RequestInit={}) {
  const r = await fetch(`/api/rdp/public${path}`, { ...opts, headers: { 'Content-Type':'application/json', ...opts.headers } })
  if (!r.ok) throw await apiErrorFromResponse(r)
  const body = await r.json().catch(() => ({}))
  return body as T
}
export const getRdpCohort = () => pub<Cohort>('/cohort')
export const submitRdpApplication = (data:Record<string,unknown>) => pub<{application_ref:string;access_token:string;status:string;message:string}>('/applications',{method:'POST',body:JSON.stringify(data)})
export const getRdpApplicationStatus = (ref:string,token:string) => pub<ApplicationStatus>(`/application-status?ref=${encodeURIComponent(ref)}&token=${encodeURIComponent(token)}`)
export const getRdpPaymentSummary = (ref:string,token:string) => pub<ApplicationStatus>(`/payment-summary?ref=${encodeURIComponent(ref)}&token=${encodeURIComponent(token)}`)
export const submitRdpScholarship = (data:Record<string,unknown>) => pub('/scholarships',{method:'POST',body:JSON.stringify(data)})
export type PaymentProviderOption = { provider:string; display_name:string; environment:string; currency:string; priority:number }
export type PaymentProviderList = { active_environment:string; allow_provider_selection:boolean; providers:PaymentProviderOption[] }
export const getRdpPaymentProviders = (ref:string,token:string,invoiceId:number) => pub<PaymentProviderList>(`/payment-providers?ref=${encodeURIComponent(ref)}&token=${encodeURIComponent(token)}&invoice_id=${invoiceId}`)
export const initRdpPayment = (data:{application_ref:string;payment_token:string;invoice_id:number;provider?:string}) => pub<{authorization_url:string;access_code?:string|null;reference:string;provider:string;environment:string}>('/payments/initialize',{method:'POST',body:JSON.stringify(data)})
export const setRdpPassword = (token:string,new_password:string) => pub<{message:string}>('/set-password',{method:'POST',body:JSON.stringify({token,new_password})})

export const requestRdpPasswordReset = (email:string) => pub<{message:string}>('/password-reset/request',{method:'POST',body:JSON.stringify({email})})

export const getRdpCatalogues=()=>pub<Catalogue[]>('/catalogue')

// Applicant credentials are sent in POST bodies, never URL query parameters,
// when retrieving or accepting an immutable programme quotation.
export type RDPQuotation = {
  preferred_package_name?: string | null
  preferred_fee_plan_name?: string | null
  preferred_total_amount_subunit?: number | null
  preferred_currency?: string | null
  application_ref: string
  quote_id: number
  quote_number: number
  status: 'offered' | 'accepted'
  package_name: string | null
  entitlements_snapshot_json: string | null
  currency: string
  gross_total_subunit: number
  scholarship_subunit: number
  payable_total_subunit: number
  effective_date: string | null
  expires_at: string | null
  accepted_at: string | null
  installments: {sequence_number: number; amount_subunit: number; due_date: string | null; description: string | null}[]
}
export type RDPQuotationAcceptance = {
  application_ref: string
  quote_id: number
  quote_status: 'accepted'
  application_status: 'payment_due'
  payment_token: string
  invoices: {sequence: number; amount_subunit: number; currency: string; due_date: string | null; status: string}[]
}
export const getRdpQuotation = (application_ref: string, access_token: string) =>
  pub<RDPQuotation>('/quotation', {
    method: 'POST', cache: 'no-store', body: JSON.stringify({application_ref, access_token}),
  })
export const acceptRdpQuotation = (application_ref: string, access_token: string, quote_id: number) =>
  pub<RDPQuotationAcceptance>(`/quotations/${quote_id}/accept`, {
    method: 'POST', cache: 'no-store', body: JSON.stringify({application_ref, access_token}),
  })
