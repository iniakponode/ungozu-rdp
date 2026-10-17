'use client'

import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { builderApi, type BuilderData } from '@/lib/rdp-builder-api'
import { userErrorMessage } from '@/lib/api-errors'
import { ApiErrorAlert } from '@/components/ui/api-error-alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

type DateField = 'application_open_date' | 'application_deadline' | 'start_date' | 'graduation_date' | 'end_date'
type Draft = {
  name: string; slug: string; label: string; capacity: number; public_summary: string
} & Record<DateField, string>
const emptyDates: Pick<Draft, DateField> = {
  application_open_date: '', application_deadline: '', start_date: '', graduation_date: '', end_date: '',
}
const dateInputs: Array<{key: DateField; label: string}> = [
  {key: 'application_open_date', label: 'Applications open'},
  {key: 'application_deadline', label: 'Application deadline'},
  {key: 'start_date', label: 'Programme starts'},
  {key: 'graduation_date', label: 'Graduation'},
  {key: 'end_date', label: 'Programme ends'},
]

export function CloneCohort({
  data, targetVersionId, onCloned,
}: {
  data: BuilderData;
  targetVersionId: number;
  onCloned: (id: number) => Promise<void>;
}) {
  const [open, setOpen] = useState(false)
  const [sourceId, setSourceId] = useState(0)
  const [form, setForm] = useState<Draft>({name: '',slug: '',label: '',capacity: 10,public_summary: '',...emptyDates})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const sources = useMemo(() => data.cohorts.filter(c =>
    c.programme_version_id !== null && data.fee_plans.some(f => f.cohort_id === c.id)
  ), [data.cohorts, data.fee_plans])
  const source = sources.find(c => c.id === sourceId)
  const plans = data.fee_plans.filter(p => p.cohort_id === sourceId)
  const sourcePackages = data.packages.filter(p => p.programme_version_id === source?.programme_version_id)
  const targetPackages = data.packages.filter(p => p.programme_version_id === targetVersionId)
  const missing = plans.flatMap(p => {
    const previous = sourcePackages.find(pkg => pkg.id === p.package_id)
    if (!previous) return [`${p.code}: source package is missing or unlinked`]
    if (!targetPackages.some(pkg => pkg.code === previous.code && pkg.is_active)) return [`${p.code}: target needs active package '${previous.code}'`]
    return []
  })
  const selectSource = (id: number) => {
    setSourceId(id); setError('')
    const c = sources.find(x => x.id === id)
    setForm({name: c ? `${c.name} (new cohort)` : '', slug: '', label: c ? `${c.label} - new cohort` : '',
      capacity: c?.capacity ?? 10, public_summary: c?.public_summary ?? '', ...emptyDates})
  }
  const edit = (key: keyof Draft, value: string | number) => setForm(prev => ({...prev, [key]: value}))
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    if (!source) {setError('Select a source cohort with fee plans.'); return}
    if (missing.length) {setError(missing.join('; ')); return}
    const {application_open_date: startApplications, application_deadline: deadline,
      start_date: starts, graduation_date: graduation, end_date: ends} = form
    if (!(startApplications <= deadline && deadline < starts && starts <= graduation && graduation <= ends)) {
      setError('Required: applications open ≤ deadline < start ≤ graduation ≤ end.'); return
    }
    if (!window.confirm(`Create a NEW UNPUBLISHED cohort and copy ${plans.length} fee plan(s)? All copied fee plans will be INACTIVE until you review them. Existing applicants and payments will not be copied.`)) return
    setBusy(true)
    try {
      const response = await builderApi<{cohort: {id: number}; copied_fee_plans: number}>(
        `/cohorts/${source.id}/clone`, 'POST', {
          ...form, programme_version_id: targetVersionId,
        },
      )
      await onCloned(response.cohort.id)
      setOpen(false); setSourceId(0)
      toast.success(`Draft cohort created with ${response.copied_fee_plans} inactive fee plan(s). Review prices and activate explicitly.`)
    } catch (failure) {
      const message = userErrorMessage(failure, 'Could not clone cohort and pricing')
      setError(message); toast.error(message)
    } finally {setBusy(false)}
  }
  return <Card className="border-dashed" id="builder-clone-cohort">
    <CardHeader><CardTitle>Clone cohort and pricing</CardTitle></CardHeader>
    <CardContent className="space-y-3">
      <p className="text-xs"><a className="text-primary underline" href="/admin/help#section-06">Read the cohort cloning and fee-plan guide</a></p>
      <p className="text-sm text-muted-foreground">Copy cohort details and fee-plan instalment schedules to a new draft. You must provide a unique slug and new dates. All copied plans are disabled pending financial review; nothing is published or charged automatically.</p>
      <Button type="button" variant="outline" disabled={!sources.length} onClick={() => {setOpen(x => !x); setError('')}}>{open ? 'Close clone form' : 'Clone cohort & pricing'}</Button>
      {!sources.length && <p className="text-sm text-muted-foreground">No versioned cohort with fee plans is available to clone.</p>}
      {open && <form onSubmit={submit} className="space-y-4 rounded-md border p-4">
        <ApiErrorAlert message={error} />
        <div><Label htmlFor="clone-source">Source cohort</Label><select id="clone-source" className="mt-1 w-full rounded-md border bg-background p-2" value={sourceId || ''} required onChange={e => selectSource(Number(e.target.value))}>
          <option value="">Select a source cohort…</option>{sources.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
        </select></div>
        {source && <>
          <div className="rounded-md border p-3 text-sm"><strong>Pricing preview ({plans.length} plans)</strong>
            <ul className="mt-2 list-disc pl-5">{plans.map(p => <li key={p.id}>{p.name}: {p.currency} {(p.total_amount_subunit / 100).toLocaleString()} · {p.installment_count} instalment(s) · copied as inactive</li>)}</ul>
            {missing.length > 0 && <p className="mt-2 text-red-700">Missing package mappings: {missing.join('; ')}</p>}
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {(['name', 'label', 'slug'] as const).map(key => <div key={key}><Label htmlFor={`clone-${key}`}>{key === 'slug' ? 'New unique cohort slug' : key === 'label' ? 'Public label' : 'New cohort name'}</Label><Input id={`clone-${key}`} required value={form[key]} onChange={e => edit(key, e.target.value)} /></div>)}
            <div><Label htmlFor="clone-capacity">Capacity</Label><Input id="clone-capacity" type="number" min={1} max={32767} required value={form.capacity} onChange={e => edit('capacity', Number(e.target.value))}/></div>
            {dateInputs.map(item => <div key={item.key}><Label htmlFor={`clone-${item.key}`}>{item.label}</Label><Input id={`clone-${item.key}`} type="date" required value={form[item.key]} onChange={e => edit(item.key, e.target.value)} /></div>)}
          </div>
          <div><Label htmlFor="clone-summary">Public summary</Label><Textarea id="clone-summary" value={form.public_summary} onChange={e => edit('public_summary', e.target.value)} /></div>
          <p className="text-sm text-muted-foreground">After cloning, open each fee plan, confirm amount, currency and due offsets, enable the approved plans, and only then publish this cohort. Applicants, invoices, payments and quotations are never copied.</p>
          <div className="flex flex-wrap gap-2"><Button disabled={busy || !!missing.length} type="submit">{busy ? 'Creating draft…' : 'Create draft clone'}</Button><Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button></div>
        </>}
      </form>}
    </CardContent>
  </Card>
}
