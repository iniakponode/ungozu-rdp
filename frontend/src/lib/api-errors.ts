/** Centralized, user-facing parsing of FastAPI and Next.js API failures. */
export class ApiRequestError extends Error {
 constructor(public readonly status:number,message:string,public readonly fieldErrors:string[]=[]){super(message);this.name='ApiRequestError'}
}
const allowed=(s:string)=>s.replace(/[\u0000-\u001f]/g,' ').trim().slice(0,350)
function fieldName(loc:unknown):string {
 if(!Array.isArray(loc)) return ''
 const parts=loc.filter(v=>typeof v==='string'||typeof v==='number').map(String).filter(v=>!['body','query','path','header'].includes(v))
 return parts.join(' → ').replaceAll('_',' ')
}
function issues(x:unknown):string[] {
 if(!Array.isArray(x))return []
 return x.slice(0,8).map(item=>{
  if(typeof item==='string')return allowed(item)
  if(!item||typeof item!=='object')return ''
  const row=item as Record<string,unknown>
  const label=fieldName(row.loc)
  const msg=typeof row.msg==='string'?row.msg:typeof row.message==='string'?row.message:''
  return allowed(label?`${label}: ${msg}`:msg)
 }).filter(Boolean)
}
function backendMessage(body:unknown):{message:string;fields:string[]} {
 if(typeof body==='string'){try{return backendMessage(JSON.parse(body))}catch{return {message:allowed(body),fields:[]}}}
 if(!body||typeof body!=='object')return {message:'',fields:[]}
 const record=body as Record<string,unknown>
 for(const candidate of [record.detail,record.errors,record.message,record.error]) {
  const messages=issues(candidate)
  if(messages.length)return {message:messages.join(' • '),fields:messages}
  if(typeof candidate==='string')return {message:allowed(candidate),fields:[]}
  if(candidate&&typeof candidate==='object') {
   const inner=candidate as Record<string,unknown>
   if(typeof inner.message==='string'){const blockers=issues(inner.blockers);return {message:allowed(inner.message)+(blockers.length?': '+blockers.join(' • '):''),fields:blockers}}
   const nested=issues(inner.errors)
   if(nested.length)return {message:nested.join(' • '),fields:nested}
  }
 }
 return {message:'',fields:[]}
}
export async function apiErrorFromResponse(res:Response,fallback='Unable to complete your request'):Promise<ApiRequestError> {
 const text=await res.text().catch(()=>'')
 const message=backendMessage(text)
 if(res.status===401)return new ApiRequestError(res.status,'Your session has expired or you are not signed in. Please sign in again.')
 if(res.status===403)return new ApiRequestError(res.status,'You do not have permission to perform this action.')
 if(res.status>=500)return new ApiRequestError(res.status,'A server problem prevented this action. Please try again or contact support.')
 if(res.status===429)return new ApiRequestError(res.status,'Too many requests. Please wait a moment and retry.')
 if(res.status===422 && message.fields.length)return new ApiRequestError(res.status,`Please correct the following: ${message.message}`,message.fields)
 return new ApiRequestError(res.status,message.message||`${fallback} (HTTP ${res.status})`,message.fields)
}
export function userErrorMessage(error:unknown,fallback='Unable to complete your request'):string {
 if(error instanceof ApiRequestError)return error.message
 if(error instanceof Error){const b=backendMessage(error.message);return b.message||fallback}
 if(typeof error==='string'){const b=backendMessage(error);return b.message||fallback}
 return fallback
}
