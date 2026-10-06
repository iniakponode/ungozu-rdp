import { NextRequest, NextResponse } from 'next/server'
import { rejectCrossSiteMutation } from '@/lib/server/request-security'
const BACKEND_URL=process.env.BACKEND_URL ?? 'http://127.0.0.1:8010'; const COOKIE='admin_token'
async function handler(request:NextRequest,{params}:{params:Promise<{path:string[]}>}){
 const originError=rejectCrossSiteMutation(request); if(originError)return originError
 const token=request.cookies.get(COOKIE)?.value; if(!token)return NextResponse.json({detail:'Not authenticated'},{status:401})
 const {path}=await params; const url=new URL(`/api/v1/rdp/admin/${path.join('/')}`,BACKEND_URL); request.nextUrl.searchParams.forEach((v,k)=>url.searchParams.set(k,v))
 const headers:HeadersInit={Authorization:`Bearer ${token}`}; const ct=request.headers.get('content-type'); if(ct)headers['Content-Type']=ct
 const body=request.method==='GET'||request.method==='HEAD'?null:await request.text()||null
 try{const r=await fetch(url.toString(),{method:request.method,headers,body});const h=new Headers();const rt=r.headers.get('content-type');if(rt)h.set('content-type',rt);return new NextResponse(r.body,{status:r.status,headers:h})}catch{return NextResponse.json({detail:'Could not reach backend.'},{status:502})}
}
export const GET=handler; export const POST=handler; export const PUT=handler; export const PATCH=handler; export const DELETE=handler
