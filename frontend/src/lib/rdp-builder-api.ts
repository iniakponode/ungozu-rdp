import { apiErrorFromResponse } from './api-errors'
/** Admin-only Programme Builder API. Proxied through the existing authenticated BFF. */
export type Programme = { id:number;name:string;slug:string;category:string|null;description:string|null;status:string;is_published:boolean }
export type Version = { id:number;programme_id:number;version_number:number;title:string;overview:string|null;duration_value:number;duration_unit:string;learning_outcomes:string|null;status:string;published_at:string|null }
export type Module = { id:number;programme_version_id:number;sequence_number:number;title:string;summary:string|null;learning_outcomes:string|null;completion_criteria:string|null;is_required:boolean;status:string }
export type CurriculumItem = { id:number;module_id:number;sequence_number:number;item_type:string;title:string;description:string|null;instructions:string|null;estimated_minutes:number|null;completion_required:boolean;status:string }
export type Package = { id:number;programme_version_id:number;code:string;name:string;description:string|null;is_active:boolean;capacity:number|null;sort_order:number }
export type Entitlement = { id:number;package_id:number;code:string;name:string;quantity:number|null;unit:string|null;limit_value:number|null;limit_unit:string|null;period:string|null;description:string|null;is_included:boolean;sort_order:number }
export type Cohort = { id:number;programme_version_id:number|null;name:string;slug:string;label:string;application_open_date:string;application_deadline:string;start_date:string;graduation_date:string;end_date:string;capacity:number;status:string;public_summary:string|null;is_published:boolean }
export type FeePlan = { id:number;cohort_id:number;package_id:number|null;code:string;region:string;name:string;currency:string;total_amount_subunit:number;installment_count:number;installment_amount_subunit:number;description:string|null;is_active:boolean;sort_order:number }
export type Instalment = { id:number;fee_plan_id:number;sequence_number:number;amount_subunit:number;due_offset_days:number;description:string|null }
export type BuilderData = {programmes:Programme[];versions:Version[];modules:Module[];items:CurriculumItem[];packages:Package[];entitlements:Entitlement[];cohorts:Cohort[];fee_plans:FeePlan[];installments:Instalment[]}
const base='/api/rdp-admin/builder'
export async function builderApi<T>(path:string, method:'GET'|'POST'|'PUT'='GET', body?:unknown):Promise<T>{
 const r=await fetch(base+path,{method,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),cache:'no-store'})
 if(!r.ok)throw await apiErrorFromResponse(r)
 return r.json() as Promise<T>
}
export const fetchBuilder=()=>builderApi<BuilderData>('/overview')
