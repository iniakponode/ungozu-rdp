import { apiErrorFromResponse } from './api-errors'
/** Milestone C: typed assessment and certificate client via existing auth proxies. */
export type Criterion = { id:number;programme_version_id:number;code:string;title:string;description:string|null;category:string;max_score:number;pass_score:number;required:boolean;sort_order:number }
export type CriterionInput = Omit<Criterion,'id'|'programme_version_id'>
export type Evaluation = {id:number;enrollment_id:number;criterion_id:number;assessor_user_id:number;score:number;evidence:string;feedback:string;assessed_at:string}
export type Decision = {id:number;enrollment_id:number;decided_by_user_id:number;decision:string;rationale:string;decided_at:string}
export type Certificate = {id:number;enrollment_id:number;certificate_number:string;verification_token:string;recipient_name_snapshot:string;programme_title_snapshot:string;cohort_label_snapshot:string;duration_snapshot:string|null;issued_at:string;revoked_at:string|null;revoke_reason:string|null}
export type CurriculumProgress = {id:number;enrollment_id:number;item_id:number;status:string;evidence:string;reviewed_feedback:string|null;submitted_at:string|null;reviewed_at:string|null}
export type CurriculumLine = {id:number;module_id:number;title:string;item_type:string;completion_required:boolean;instructions:string|null;progress:CurriculumProgress|null}
export type Completion = {enrollment_id:number;programme_version_id:number;programme_title:string;completion_status:string;criteria:Array<Criterion & {evaluation:Evaluation|null;passed:boolean}>;curriculum:CurriculumLine[];blockers?:string[];can_approve:boolean;decisions?:Decision[];certificate:Certificate|null}
export type Verification = {valid:boolean;status:'valid'|'revoked';certificate_number:string;recipient_name:string;programme_title:string;cohort_label:string;duration:string|null;issued_at:string}
async function call<T>(path:string,opts:RequestInit={}){
 const res=await fetch(path,{...opts,cache:'no-store',headers:{'Content-Type':'application/json',...opts.headers}})
 if(!res.ok)throw await apiErrorFromResponse(res)
 const body=await res.json().catch(()=>({}))
 return body as T
}
const admin='/api/rdp-admin'
const post=<T>(path:string,payload:unknown)=>call<T>(admin+path,{method:'POST',body:JSON.stringify(payload)})
export const listCriteria=(id:number)=>call<Criterion[]>(`${admin}/assessment-criteria/${id}`)
export const createCriterion=(id:number,payload:CriterionInput)=>post<Criterion>(`/assessment-criteria/${id}`,payload)
export const editCriterion=(id:number,payload:CriterionInput)=>call<Criterion>(`${admin}/assessment-criteria/criterion/${id}`,{method:'PUT',body:JSON.stringify(payload)})
export const adminCompletion=(id:number)=>call<Completion>(`${admin}/completion/${id}`)
export const evaluateCriterion=(id:number,payload:{criterion_id:number;score:number;evidence:string;feedback:string})=>post<Evaluation>(`/completion/${id}/evaluations`,payload)
export const completionDecision=(id:number,payload:{decision:'approved'|'needs_work'|'not_approved';rationale:string})=>post<Decision>(`/completion/${id}/decisions`,payload)
export const issueCertificate=(id:number)=>post<Certificate>(`/completion/${id}/certificate`,{})
export const revokeCertificate=(id:number,reason:string)=>post<Certificate>(`/completion/${id}/certificate/revoke`,{reason})
export const participantCompletion=(id:number)=>call<Completion>(`/api/rdp-portal/completion?enrollment_id=${id}`)

export const adminCurriculum=(id:number)=>call<CurriculumLine[]>(`${admin}/completion/${id}/curriculum`)
export const reviewCurriculum=(id:number,itemId:number,status:'reviewed'|'needs_work',feedback:string)=>post<CurriculumProgress>(`/completion/${id}/curriculum/${itemId}/review`,{status,feedback})
export const participantCurriculum=(id:number)=>call<CurriculumLine[]>(`/api/rdp-portal/curriculum?enrollment_id=${id}`)
export const submitCurriculum=(id:number,itemId:number,evidence:string,submit=true)=>call<CurriculumProgress>(`/api/rdp-portal/curriculum/${itemId}?enrollment_id=${id}`,{method:'PUT',body:JSON.stringify({evidence,submit})})
