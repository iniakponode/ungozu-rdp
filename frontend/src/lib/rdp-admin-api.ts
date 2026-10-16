export class ApiError extends Error { constructor(public status:number,message:string){super(message)} }
async function apiFetch<T>(path:string,options:RequestInit={}):Promise<T>{
 const res=await fetch(`/api/rdp-admin${path}`,{headers:{'Content-Type':'application/json',...options.headers},...options})
 if(!res.ok){throw new ApiError(res.status,await res.text())}
 if(res.status===204)return undefined as T
 return res.json() as Promise<T>
}
export interface RDPDashboardStats {
 total_applications:number
 submitted:number
 screening:number
 shortlisted:number
 accepted_or_payment_due:number
 enrolled:number
 waitlisted:number
 declined:number
 scholarship_requests:number
 scholarship_approved:number
 payments_successful:number
 revenue_ngn_subunit:number
 revenue_usd_subunit:number
 revenue_by_currency_subunit:Record<string,number>
 cohort_capacity:number
}
export interface RDPFeePlan { id:number; code:string; region:string; name:string; currency:string; total_amount_subunit:number; installment_count:number; installment_amount_subunit:number; description?:string|null; is_active:boolean }
export interface RDPReview { id:number; application_id:number; reviewer_id:number; motivation_score:number; development_need_score:number; programme_fit_score:number; commitment_score:number; potential_score:number; total_score:number; recommendation:string; notes?:string|null; reviewer_name?:string|null }
export interface RDPScholarship { id:number; application_id:number; support_type:string; financial_need:string; possible_contribution?:string|null; support_case:string; status:string; approved_amount_subunit?:number|null; approved_currency?:string|null; admin_notes?:string|null }
export interface RDPInvoice { id:number; sequence:number; amount_subunit:number; currency:string; due_date?:string|null; status:string; paid_at?:string|null }
export interface RDPApplicationAdmin { id:number; cohort_id:number; application_ref:string; full_name:string; email:string; country:string; institution:string; career_stage:string; discipline:string; research_interests:string; goals:string; challenges:string; current_outputs?:string|null; commitment:string; scholarship_interest:boolean; referral_source?:string|null; status:string; fee_plan_id?:number|null; acceptance_deadline?:string|null; admission_notes?:string|null; submitted_at:string; decided_at?:string|null; fee_plan?:RDPFeePlan|null; reviews:RDPReview[]; scholarship_request?:RDPScholarship|null; invoices:RDPInvoice[] }
export interface RDPEnrollment { id:number; cohort_id:number; application_id:number; user_id:number; status:string; enrolled_at:string; completion_status:string; certificate_number?:string|null; full_name?:string|null; email?:string|null }
export interface RDPPaymentAdmin { id:number; invoice_id:number; reference:string; provider:string; environment:string; amount_subunit:number; currency:string; status:string; provider_id?:string|null; provider_session_id?:string|null; paid_at?:string|null; created_at:string }
export const getRDPDashboard=(cohortId?:number)=>apiFetch<RDPDashboardStats>(`/dashboard${cohortId===undefined?'':`?cohort_id=${cohortId}`}`)
export const getRDPApplications=(params?:{status?:string;q?:string;cohort_id?:number})=>{const qs=params?`?${new URLSearchParams(Object.entries(params).filter(([,v])=>v).map(([k,v])=>[k,String(v)])).toString()}`:'';return apiFetch<RDPApplicationAdmin[]>(`/applications${qs}`)}
export const getRDPApplication=(id:number)=>apiFetch<RDPApplicationAdmin>(`/applications/${id}`)
export const saveRDPReview=(id:number,data:{motivation_score:number;development_need_score:number;programme_fit_score:number;commitment_score:number;potential_score:number;recommendation:string;notes?:string})=>apiFetch<RDPReview>(`/applications/${id}/review`,{method:'PUT',body:JSON.stringify(data)})
export const decideRDPApplication=(id:number,data:{decision:string;fee_plan_id?:number;acceptance_deadline?:string;admission_notes?:string})=>apiFetch<{status:string;payment_link?:string|null;email_sent:boolean}>(`/applications/${id}/decision`,{method:'POST',body:JSON.stringify(data)})
export const decideRDPScholarship=(id:number,data:{status:string;approved_amount_subunit?:number;approved_currency?:string;admin_notes?:string})=>apiFetch<RDPScholarship>(`/scholarships/${id}`,{method:'PUT',body:JSON.stringify(data)})
export const getRDPEnrollments=(cohortId?:number)=>apiFetch<RDPEnrollment[]>(`/enrollments${cohortId===undefined?'':`?cohort_id=${cohortId}`}`)
export const getRDPPayments=(cohortId?:number)=>apiFetch<RDPPaymentAdmin[]>(`/payments${cohortId===undefined?'':`?cohort_id=${cohortId}`}`)
export interface RDPDevelopmentPlanAdmin { id:number; enrollment_id:number; researcher_identity?:string|null; twelve_month_goal?:string|null; publication_goal?:string|null; methods_goal?:string|null; funding_goal?:string|null; network_goal?:string|null; impact_goal?:string|null; mentor_notes?:string|null; status:string }
export interface RDPCheckInAdmin { id:number; enrollment_id:number; month_number:number; progress_summary?:string|null; outputs_this_month?:string|null; obstacles?:string|null; next_actions?:string|null; support_requested?:string|null; mentor_feedback?:string|null; status:string; submitted_at?:string|null; reviewed_at?:string|null }
export interface RDPEnrollmentAdminDetail { enrollment:RDPEnrollment; cohort:{id:number;name:string;slug:string;label:string;application_open_date:string;application_deadline:string;start_date:string;graduation_date:string;end_date:string;capacity:number;status:string}; development_plan?:RDPDevelopmentPlanAdmin|null; checkins:RDPCheckInAdmin[]; invoices:RDPInvoice[] }
export interface RDPEventAdmin { id:number;cohort_id:number;title:string;event_type:string;starts_at:string;ends_at?:string|null;delivery_mode?:string|null;meeting_url?:string|null;description?:string|null;is_published:boolean }
export interface RDPResourceAdmin { id:number;cohort_id:number;title:string;resource_type:string;url?:string|null;description?:string|null;month_number?:number|null;sort_order:number;is_published:boolean }
export type RDPEventInput=Omit<RDPEventAdmin,'id'|'cohort_id'>; export type RDPResourceInput=Omit<RDPResourceAdmin,'id'|'cohort_id'>
export const getRDPEnrollment=(id:number)=>apiFetch<RDPEnrollmentAdminDetail>(`/enrollments/${id}`)
export const reviewRDPDevelopmentPlan=(id:number,data:{mentor_notes?:string;status?:string})=>apiFetch<RDPDevelopmentPlanAdmin>(`/enrollments/${id}/development-plan`,{method:'PUT',body:JSON.stringify(data)})
export const reviewRDPCheckIn=(id:number,data:{mentor_feedback?:string;status?:string})=>apiFetch<RDPCheckInAdmin>(`/checkins/${id}`,{method:'PUT',body:JSON.stringify(data)})
export const getRDPEvents=()=>apiFetch<RDPEventAdmin[]>('/events'); export const createRDPEvent=(data:RDPEventInput)=>apiFetch<RDPEventAdmin>('/events',{method:'POST',body:JSON.stringify(data)}); export const updateRDPEvent=(id:number,data:RDPEventInput)=>apiFetch<RDPEventAdmin>(`/events/${id}`,{method:'PUT',body:JSON.stringify(data)}); export const deleteRDPEvent=(id:number)=>apiFetch<void>(`/events/${id}`,{method:'DELETE'})
export const getRDPResources=()=>apiFetch<RDPResourceAdmin[]>('/resources'); export const createRDPResource=(data:RDPResourceInput)=>apiFetch<RDPResourceAdmin>('/resources',{method:'POST',body:JSON.stringify(data)}); export const updateRDPResource=(id:number,data:RDPResourceInput)=>apiFetch<RDPResourceAdmin>(`/resources/${id}`,{method:'PUT',body:JSON.stringify(data)}); export const deleteRDPResource=(id:number)=>apiFetch<void>(`/resources/${id}`,{method:'DELETE'})
export interface RDPPaymentPlatformSettings { active_environment:'test'|'live';allow_provider_selection:boolean }
export interface RDPPaymentProviderConfig { provider:'paystack'|'stripe';environment:'test'|'live';display_name:string;is_enabled:boolean;public_key?:string|null;secret_configured:boolean;webhook_secret_configured:boolean;secret_key_masked?:string|null;webhook_secret_masked?:string|null;supported_currencies:string[];priority:number;last_tested_at?:string|null;last_test_status?:string|null;last_test_message?:string|null;source:string;webhook_url:string;callback_url:string }
export interface RDPPaymentProviderHealth { provider:string;environment:string;display_name:string;enabled:boolean;configured:boolean;connection_status?:string|null;last_tested_at?:string|null;last_test_message?:string|null;last_webhook_at?:string|null;webhook_status?:string|null;successful_payments:number;failed_payments:number }
export interface RDPPaymentHealth { active_environment:string;providers:RDPPaymentProviderHealth[] }
export interface RDPPaymentAudit { id:number;admin_user_id?:number|null;action:string;provider?:string|null;environment?:string|null;details?:string|null;created_at:string }
export const getRDPPaymentSettings=()=>apiFetch<RDPPaymentPlatformSettings>('/payment-settings'); export const updateRDPPaymentSettings=(data:{active_environment:'test'|'live';allow_provider_selection:boolean;current_password?:string})=>apiFetch<RDPPaymentPlatformSettings>('/payment-settings',{method:'PUT',body:JSON.stringify(data)})
export const getRDPPaymentProviders=()=>apiFetch<RDPPaymentProviderConfig[]>('/payment-providers'); export const saveRDPPaymentProvider=(provider:string,environment:string,data:{display_name?:string;is_enabled?:boolean;public_key?:string;secret_key?:string;webhook_secret?:string;supported_currencies?:string[];priority?:number;current_password?:string})=>apiFetch<RDPPaymentProviderConfig>(`/payment-providers/${provider}/${environment}`,{method:'PUT',body:JSON.stringify(data)}); export const testRDPPaymentProvider=(provider:string,environment:string)=>apiFetch<{provider:string;environment:string;success:boolean;message:string;tested_at:string}>(`/payment-providers/${provider}/${environment}/test`,{method:'POST'}); export const getRDPPaymentHealth=(environment?:string)=>apiFetch<RDPPaymentHealth>(`/payment-health${environment?`?environment=${encodeURIComponent(environment)}`:''}`); export const getRDPPaymentAudit=()=>apiFetch<RDPPaymentAudit[]>('/payment-audit')
