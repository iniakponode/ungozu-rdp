'use client'
import { FormEvent, useState } from 'react'
import { useRouter } from 'next/navigation'
import { requestRdpPasswordReset } from '@/lib/rdp-api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RDPSectionHeading } from '@/components/rdp/rdp-ui'

export default function LoginPage(){
 const router=useRouter();const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[resetMsg,setResetMsg]=useState('')
 async function login(e:FormEvent){e.preventDefault();setBusy(true);setError('');try{const r=await fetch('/api/auth/rdp-login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});const b=await r.json().catch(()=>({}));if(!r.ok)throw new Error(b.error??'Login failed');router.push('/portal');router.refresh()}catch(e){setError(e instanceof Error?e.message:'Login failed')}finally{setBusy(false)}}
 async function reset(){if(!email){setResetMsg('Enter your email first.');return}try{const r=await requestRdpPasswordReset(email);setResetMsg(r.message)}catch(e){setResetMsg(e instanceof Error?e.message:'Could not request reset')}}
 return <div className="mx-auto max-w-xl px-4 py-14 sm:px-6"><RDPSectionHeading eyebrow="Participant portal" title="Sign in" text="Participant access is activated after enrolment. Use the password you created from your secure setup email."/><Card className="mt-8"><CardHeader><CardTitle className="text-lg">Programme participant login</CardTitle></CardHeader><CardContent><form onSubmit={login} className="space-y-4"><div><Label>Email</Label><Input type="email" value={email} onChange={e=>setEmail(e.target.value)} required/></div><div><Label>Password</Label><Input type="password" value={password} onChange={e=>setPassword(e.target.value)} required/></div>{error&&<p className="text-sm text-destructive">{error}</p>}<Button className="w-full" disabled={busy}>{busy?'Signing in…':'Sign in'}</Button></form><div className="mt-5 border-t border-border pt-4"><button onClick={reset} className="text-sm text-primary hover:underline">Forgot your password?</button>{resetMsg&&<p className="mt-2 text-xs text-muted-foreground">{resetMsg}</p>}</div></CardContent></Card></div>
}
