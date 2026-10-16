import type { Catalogue } from './rdp-catalogue'
import type { Cohort, Invoice } from './rdp-api'
export type DevelopmentPlan = { id:number; enrollment_id:number; researcher_identity?:string|null; twelve_month_goal?:string|null; publication_goal?:string|null; methods_goal?:string|null; funding_goal?:string|null; network_goal?:string|null; impact_goal?:string|null; mentor_notes?:string|null; status:string }
export type CheckIn = { id:number; enrollment_id:number; month_number:number; progress_summary?:string|null; outputs_this_month?:string|null; obstacles?:string|null; next_actions?:string|null; support_requested?:string|null; mentor_feedback?:string|null; status:string; submitted_at?:string|null }
export type PortalDashboard = { enrollment:{id:number;status:string;completion_status:string;full_name?:string|null;email?:string|null}; cohort:Cohort; development_plan?:DevelopmentPlan|null; checkins:CheckIn[]; upcoming_events:Array<{id:number;title:string;event_type:string;starts_at:string;delivery_mode?:string|null;meeting_url?:string|null;description?:string|null}>; resources:Array<{id:number;title:string;resource_type:string;url?:string|null;description?:string|null;month_number?:number|null}>; invoices:Invoice[] }
async function req<T>(path:string,opts:RequestInit={}){ const r=await fetch(`/api/rdp-portal${path}`,{...opts,headers:{'Content-Type':'application/json',...opts.headers}}); const b=await r.json().catch(()=>({})); if(!r.ok) throw new Error(b.detail??'Request failed'); return b as T }
export type PortalEnrollment = { id:number; cohort_id:number; cohort_label:string; status:string; start_date:string; end_date:string }
export const getRdpPortalEnrollments=()=>req<PortalEnrollment[]>('/enrolments')
export const getRdpPortalDashboard=(id?:number)=>req<PortalDashboard>(`/dashboard${id==null?'':`?enrollment_id=${id}`}`)
export const updateRdpDevelopmentPlan=(data:Partial<DevelopmentPlan>,id?:number)=>req<DevelopmentPlan>(`/development-plan${id==null?'':`?enrollment_id=${id}`}`,{method:'PUT',body:JSON.stringify(data)})
export const updateRdpCheckIn=(month:number,data:Partial<CheckIn>,id?:number)=>req<CheckIn>(`/checkins/${month}${id==null?'':`?enrollment_id=${id}`}`,{method:'PUT',body:JSON.stringify(data)})

export const getRdpPortalCatalogue=(id?:number)=>req<Catalogue & {enrolled_package_id:number|null;enrolled_fee_plan_id:number|null}>(`/catalogue${id==null?'':`?enrollment_id=${id}`}`)
