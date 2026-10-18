'use client'
import { userErrorMessage } from '@/lib/api-errors'
import { AdminHelpLink } from '@/components/rdp/help-link'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { CircleCheck, CircleX, KeyRound, RefreshCw, ShieldCheck } from 'lucide-react'
import {
  getRDPPaymentAudit,
  getRDPPaymentHealth,
  getRDPPaymentProviders,
  getRDPPaymentSettings,
  saveRDPPaymentProvider,
  testRDPPaymentProvider,
  updateRDPPaymentSettings,
  type RDPPaymentAudit,
  type RDPPaymentHealth,
  type RDPPaymentPlatformSettings,
  type RDPPaymentProviderConfig,
} from '@/lib/rdp-admin-api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { PasswordInput } from '@/components/ui/password-input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'

const COMMON_CURRENCIES = ['NGN', 'USD', 'GBP', 'EUR', 'CAD', 'AUD']

type Environment = 'test' | 'live'

function statusBadge(status?: string | null) {
  if (status === 'success') return <Badge className="gap-1"><CircleCheck className="h-3 w-3"/>Verified</Badge>
  if (status === 'failed' || status === 'error') return <Badge variant="destructive" className="gap-1"><CircleX className="h-3 w-3"/>Failed</Badge>
  return <Badge variant="outline">Not tested</Badge>
}

function ProviderCard({config,onSaved}:{config:RDPPaymentProviderConfig;onSaved:()=>Promise<void>}) {
  const [displayName,setDisplayName]=useState(config.display_name)
  const [publicKey,setPublicKey]=useState(config.public_key ?? '')
  const [secretKey,setSecretKey]=useState('')
  const [webhookSecret,setWebhookSecret]=useState('')
  const [currencies,setCurrencies]=useState<string[]>(config.supported_currencies)
  const [priority,setPriority]=useState(config.priority)
  const [enabled,setEnabled]=useState(config.is_enabled)
  const [password,setPassword]=useState('')
  const [busy,setBusy]=useState(false)
  const [testing,setTesting]=useState(false)

  useEffect(()=>{
    setDisplayName(config.display_name)
    setPublicKey(config.public_key ?? '')
    setCurrencies(config.supported_currencies)
    setPriority(config.priority)
    setEnabled(config.is_enabled)
    setSecretKey('')
    setWebhookSecret('')
    setPassword('')
  },[config])

  function toggleCurrency(code:string){
    setCurrencies(current=>current.includes(code)?current.filter(x=>x!==code):[...current,code])
  }

  async function save(){
    if (!currencies.length){toast.error('Select at least one currency');return}
    if (config.environment==='live'&&!password){toast.error('Enter your administrator password to change LIVE settings');return}
    setBusy(true)
    try{
      await saveRDPPaymentProvider(config.provider,config.environment,{
        display_name:displayName,
        is_enabled:enabled,
        public_key:publicKey,
        secret_key:secretKey||undefined,
        webhook_secret:webhookSecret||undefined,
        supported_currencies:currencies,
        priority,
        current_password:password||undefined,
      })
      toast.success(`${config.display_name} ${config.environment.toUpperCase()} settings saved`)
      await onSaved()
    }catch(error){toast.error(userErrorMessage(error,'Unable to save provider'))}
    finally{setBusy(false)}
  }

  async function test(){
    setTesting(true)
    try{
      const result=await testRDPPaymentProvider(config.provider,config.environment)
      result.success?toast.success(result.message):toast.error(result.message)
      await onSaved()
    }catch(error){toast.error(userErrorMessage(error,'Connection test failed'))}
    finally{setTesting(false)}
  }

  return <Card>
    <CardHeader>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <CardTitle className="flex items-center gap-2"><KeyRound className="h-5 w-5"/>{config.display_name}</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">{config.provider} · {config.environment.toUpperCase()} · source: {config.source}</p>
        </div>
        <div className="flex items-center gap-2">{statusBadge(config.last_test_status)}<Badge variant={enabled?'default':'outline'}>{enabled?'Enabled':'Disabled'}</Badge></div>
      </div>
    </CardHeader>
    <CardContent className="space-y-5">
      {config.last_test_message&&<p className="rounded-md bg-muted p-3 text-xs">{config.last_test_message}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2"><Label>Display name</Label><Input value={displayName} onChange={e=>setDisplayName(e.target.value)}/></div>
        <div className="space-y-2"><Label>Routing priority</Label><Input type="number" min={1} max={999} value={priority} onChange={e=>setPriority(Number(e.target.value)||1)}/><p className="text-xs text-muted-foreground">Lower numbers appear first.</p></div>
        <div className="space-y-2"><Label>{config.provider==='stripe'?'Publishable key':'Public key'}</Label><Input autoComplete="off" value={publicKey} onChange={e=>setPublicKey(e.target.value)} placeholder={config.environment==='test'?'pk_test_…':'pk_live_…'}/></div>
        <div className="space-y-2"><Label>Secret key</Label><Input type="password" autoComplete="new-password" value={secretKey} onChange={e=>setSecretKey(e.target.value)} placeholder={config.secret_configured?`${config.secret_key_masked ?? 'Configured'} — leave blank to keep`:'Enter secret key'}/></div>
        {config.provider==='stripe'&&<div className="space-y-2 md:col-span-2"><Label>Webhook signing secret</Label><Input type="password" autoComplete="new-password" value={webhookSecret} onChange={e=>setWebhookSecret(e.target.value)} placeholder={config.webhook_secret_configured?`${config.webhook_secret_masked ?? 'Configured'} — leave blank to keep`:'whsec_…'}/></div>}
      </div>
      <div className="space-y-2"><Label>Accepted currencies</Label><div className="flex flex-wrap gap-3">{COMMON_CURRENCIES.map(code=><label key={code} className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm"><input type="checkbox" checked={currencies.includes(code)} onChange={()=>toggleCurrency(code)}/>{code}</label>)}</div></div>
      <div className="grid gap-3 text-xs md:grid-cols-2">
        <div><Label>Webhook URL</Label><Input readOnly value={config.webhook_url} className="mt-2 font-mono text-xs"/></div>
        <div><Label>Callback URL</Label><Input readOnly value={config.callback_url} className="mt-2 font-mono text-xs"/></div>
      </div>
      {config.environment==='live'&&<div className="space-y-2 rounded-md border border-amber-500/40 bg-amber-500/5 p-4"><Label>Administrator password</Label><PasswordInput autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Required for LIVE changes"/><p className="text-xs text-muted-foreground">Live credential changes require re-authentication.</p></div>}
      <label className="flex items-start gap-3 rounded-md border p-4 text-sm"><input type="checkbox" className="mt-1" checked={enabled} onChange={e=>setEnabled(e.target.checked)}/><span><b>Enable {config.display_name} in {config.environment.toUpperCase()}</b><br/><span className="text-xs text-muted-foreground">Only enabled providers with valid credentials and a matching invoice currency are offered to participants.</span></span></label>
      <div className="flex flex-wrap gap-2"><Button onClick={save} disabled={busy}>{busy?'Saving…':'Save configuration'}</Button><Button variant="outline" onClick={test} disabled={testing||!config.secret_configured}>{testing?<><RefreshCw className="mr-2 h-4 w-4 animate-spin"/>Testing…</>:'Test connection'}</Button></div>
    </CardContent>
  </Card>
}

export default function PaymentSettingsPage(){
  const [settings,setSettings]=useState<RDPPaymentPlatformSettings|null>(null)
  const [providers,setProviders]=useState<RDPPaymentProviderConfig[]>([])
  const [health,setHealth]=useState<RDPPaymentHealth|null>(null)
  const [audit,setAudit]=useState<RDPPaymentAudit[]>([])
  const [viewEnvironment,setViewEnvironment]=useState<Environment>('test')
  const [activeEnvironment,setActiveEnvironment]=useState<Environment>('test')
  const [allowSelection,setAllowSelection]=useState(true)
  const [password,setPassword]=useState('')
  const [savingPlatform,setSavingPlatform]=useState(false)

  async function load(){
    try{
      const [s,p,a]=await Promise.all([getRDPPaymentSettings(),getRDPPaymentProviders(),getRDPPaymentAudit()])
      setSettings(s);setActiveEnvironment(s.active_environment);setAllowSelection(s.allow_provider_selection);setProviders(p);setAudit(a)
      const h=await getRDPPaymentHealth(viewEnvironment);setHealth(h)
    }catch(error){toast.error(userErrorMessage(error,'Unable to load payment settings'))}
  }
  useEffect(()=>{void load()},[])
  useEffect(()=>{getRDPPaymentHealth(viewEnvironment).then(setHealth).catch(()=>{})},[viewEnvironment])

  const shown=useMemo(()=>providers.filter(p=>p.environment===viewEnvironment),[providers,viewEnvironment])

  async function savePlatform(){
    if (activeEnvironment==='live'&&settings?.active_environment!=='live'&&!password){toast.error('Enter your administrator password before activating LIVE payments');return}
    setSavingPlatform(true)
    try{
      const updated=await updateRDPPaymentSettings({active_environment:activeEnvironment,allow_provider_selection:allowSelection,current_password:password||undefined})
      setSettings(updated);setPassword('');toast.success('Payment platform settings saved');await load()
    }catch(error){toast.error(userErrorMessage(error,'Unable to update payment platform'))}
    finally{setSavingPlatform(false)}
  }

  return <div className="space-y-8">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-sm text-muted-foreground">Ungozu R & D · Payment gateway manager</p><h1 className="text-2xl font-bold">Payment Integration Settings</h1><AdminHelpLink topic="payments"/><p className="mt-1 max-w-3xl text-sm text-muted-foreground">Enter Paystack and Stripe credentials using the administrator-only form. Secret keys are submitted securely, encrypted before storage and masked in later API responses. Never place credentials in source code or public environment variables.</p></div><Button asChild variant="outline"><Link href="/admin">Back to programme dashboard</Link></Button></div>

    <Card><CardHeader><CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5"/>Platform controls</CardTitle></CardHeader><CardContent className="grid gap-5 md:grid-cols-2">
      <div className="space-y-2"><Label>Active payment environment</Label><select className="h-10 w-full rounded-md border bg-background px-3 text-sm" value={activeEnvironment} onChange={e=>setActiveEnvironment(e.target.value as Environment)}><option value="test">TEST — no real money</option><option value="live">LIVE — real payments</option></select><p className="text-xs text-muted-foreground">The participant checkout only uses providers configured in this environment.</p></div>
      <label className="flex items-start gap-3 rounded-md border p-4 text-sm"><input type="checkbox" className="mt-1" checked={allowSelection} onChange={e=>setAllowSelection(e.target.checked)}/><span><b>Allow participant to choose provider</b><br/><span className="text-xs text-muted-foreground">If disabled, the eligible provider with the lowest routing priority is selected automatically.</span></span></label>
      {activeEnvironment==='live'&&settings?.active_environment!=='live'&&<div className="space-y-2 md:col-span-2"><Label>Administrator password</Label><PasswordInput autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Required to switch TEST → LIVE"/></div>}
      <div className="md:col-span-2"><Button onClick={savePlatform} disabled={savingPlatform}>{savingPlatform?'Saving…':'Save platform settings'}</Button></div>
    </CardContent></Card>

    <div className="flex gap-2"><Button size="sm" variant={viewEnvironment==='test'?'default':'outline'} onClick={()=>setViewEnvironment('test')}>TEST credentials</Button><Button size="sm" variant={viewEnvironment==='live'?'default':'outline'} onClick={()=>setViewEnvironment('live')}>LIVE credentials</Button></div>
    <div className="grid gap-6 xl:grid-cols-2">{shown.map(config=><ProviderCard key={`${config.provider}-${config.environment}`} config={config} onSaved={load}/>)}</div>

    <Card><CardHeader><CardTitle>Payment integration health · {viewEnvironment.toUpperCase()}</CardTitle></CardHeader><CardContent><div className="grid gap-4 md:grid-cols-2">{health?.providers.map(item=><div key={item.provider} className="rounded-lg border p-4"><div className="flex items-center justify-between"><b>{item.display_name}</b><Badge variant={item.enabled?'default':'outline'}>{item.enabled?'Enabled':'Disabled'}</Badge></div><div className="mt-3 grid grid-cols-2 gap-2 text-xs"><span className="text-muted-foreground">Credentials</span><span>{item.configured?'Configured':'Missing'}</span><span className="text-muted-foreground">Connection</span><span>{item.connection_status??'Not tested'}</span><span className="text-muted-foreground">Last webhook</span><span>{item.last_webhook_at?new Date(item.last_webhook_at).toLocaleString('en-GB'):'None yet'}</span><span className="text-muted-foreground">Webhook status</span><span>{item.webhook_status??'—'}</span><span className="text-muted-foreground">Successful payments</span><span>{item.successful_payments}</span><span className="text-muted-foreground">Failed payments</span><span>{item.failed_payments}</span></div></div>)}</div></CardContent></Card>

    <Card><CardHeader><CardTitle>Payment configuration audit trail</CardTitle></CardHeader><CardContent>{audit.length?<div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left"><th className="p-2">When</th><th className="p-2">Action</th><th className="p-2">Provider</th><th className="p-2">Environment</th><th className="p-2">Details</th></tr></thead><tbody>{audit.map(item=><tr key={item.id} className="border-b align-top"><td className="p-2 whitespace-nowrap text-xs">{new Date(item.created_at).toLocaleString('en-GB')}</td><td className="p-2">{item.action.replaceAll('_',' ')}</td><td className="p-2">{item.provider??'—'}</td><td className="p-2">{item.environment??'—'}</td><td className="p-2 max-w-lg break-words font-mono text-xs text-muted-foreground">{item.details??'—'}</td></tr>)}</tbody></table></div>:<p className="text-sm text-muted-foreground">No payment configuration changes recorded yet.</p>}</CardContent></Card>
  </div>
}
