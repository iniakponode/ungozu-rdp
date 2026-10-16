import 'server-only'
import type { Verification } from '@/lib/rdp-completion-api'
export async function verifiedCertificate(token:string):Promise<Verification|null>{
 if(!/^[a-zA-Z0-9_-]{43}$/.test(token))return null
 const backend=process.env.BACKEND_URL??'http://127.0.0.1:8010'
 try{const res=await fetch(new URL(`/api/v1/rdp/public/certificates/${encodeURIComponent(token)}`,backend),{cache:'no-store'});if(!res.ok)return null;return await res.json() as Verification}catch{return null}
}
