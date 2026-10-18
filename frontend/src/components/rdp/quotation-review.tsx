'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  acceptRdpQuotation,
  getRdpQuotation,
  type RDPQuotation,
} from '@/lib/rdp-api'
import { userErrorMessage } from '@/lib/api-errors'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { formatMoney } from '@/components/rdp/rdp-ui'

type IncludedService = {
  code?: string
  name: string
  quantity?: number | null
  unit?: string | null
  limit_value?: number | null
  limit_unit?: string | null
  description?: string | null
  is_included?: boolean
}

function servicesFromSnapshot(raw: string | null): IncludedService[] {
  if (!raw) return []
  try {
    const data: unknown = JSON.parse(raw)
    if (!data || typeof data !== 'object' || !('items' in data)) return []
    const entries = (data as { items?: unknown }).items
    if (!Array.isArray(entries)) return []
    return entries.filter((entry): entry is IncludedService =>
      entry !== null && typeof entry === 'object' &&
      typeof (entry as IncludedService).name === 'string' &&
      (entry as IncludedService).is_included !== false,
    )
  } catch {
    return []
  }
}

function localDate(date: string | null | undefined): string {
  if (!date) return 'Not specified'
  const parsed = new Date(/^\d{4}-\d{2}-\d{2}$/.test(date) ? `${date}T12:00:00` : date)
  return Number.isNaN(parsed.getTime()) ? date : parsed.toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

function localDateTime(date: string): string {
  // Python's naive acceptance timestamps in this API are in UTC.
  const iso = /(?:Z|[+-]\d{2}:\d{2})$/.test(date) ? date : `${date}Z`
  const parsed = new Date(iso)
  return Number.isNaN(parsed.getTime()) ? date : parsed.toLocaleString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short',
  })
}

export default function QuotationReview({ reference, accessToken }: {
  reference: string
  accessToken: string
}) {
  const [quotation, setQuotation] = useState<RDPQuotation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [agreed, setAgreed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [paymentUrl, setPaymentUrl] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    getRdpQuotation(reference, accessToken)
      .then(result => { if (active) setQuotation(result) })
      .catch(e => { if (active) setError(userErrorMessage(e, 'Could not load your quotation')) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [reference, accessToken, attempt])

  const services = useMemo(() => servicesFromSnapshot(quotation?.entitlements_snapshot_json ?? null), [quotation?.entitlements_snapshot_json])
  const expiryRaw = quotation?.expires_at
  const expired = Boolean(expiryRaw && new Date(
    /(?:Z|[+-]\d{2}:\d{2})$/.test(expiryRaw) ? expiryRaw : `${expiryRaw}Z`,
  ).getTime() <= Date.now())

  async function accept() {
    if (!quotation || quotation.status !== 'offered' || !agreed || expired || busy) return
    setBusy(true)
    setError('')
    try {
      const result = await acceptRdpQuotation(reference, accessToken, quotation.quote_id)
      // The payment credential is returned only after the backend commits acceptance.
      // Do not log, persist or email this URL from the browser.
      const next = `/payment?ref=${encodeURIComponent(result.application_ref)}&token=${encodeURIComponent(result.payment_token)}`
      setPaymentUrl(next)
      window.location.assign(next)
    } catch (e) {
      setError(userErrorMessage(e, 'We could not accept your quotation. Please try again.'))
    } finally {
      setBusy(false)
    }
  }

  return <Card id="quotation-review" className="border-primary/30">
    <CardHeader><CardTitle>Review your programme quotation</CardTitle></CardHeader>
    <CardContent className="space-y-5 text-sm">
      <p>Before paying, please review your mentoring package, the amount due and the payment schedule. Accepting this quotation creates your payment invoices; it does not charge you.</p>
      {loading && <p role="status">Loading your quotation…</p>}
      {error && <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-destructive">{error}</div>}
      {!loading && !quotation && <Button type="button" variant="outline" onClick={() => setAttempt(a => a + 1)}>Try again</Button>}
      {quotation && <>
        <div className="rounded-lg border p-4 space-y-2">
          <p><b>Quotation:</b> #{quotation.quote_number}</p>
          <p><b>Package:</b> {quotation.package_name || 'Programme mentoring package'}</p>
          <p><b>Issue date:</b> {localDate(quotation.effective_date)}</p>
          {quotation.expires_at && <p><b>Accept by:</b> {localDateTime(quotation.expires_at)}</p>}
          {expired && quotation.status === 'offered' && <p className="font-medium text-destructive">This quotation has expired. Please contact the programme team about your offer.</p>}
        </div>
        <div>
          <h3 className="font-semibold">Included services</h3>
          {services.length > 0 ? <ul className="mt-2 list-disc space-y-2 pl-5">
            {services.map((item, index) => <li key={`${item.code ?? item.name}-${index}`}>
              <span className="font-medium">{item.name}</span>
              {item.quantity != null && <span> — {item.quantity} {item.unit || ''}</span>}
              {item.limit_value != null && <span> (limit: {item.limit_value} {item.limit_unit || ''})</span>}
              {item.description && <p className="text-muted-foreground">{item.description}</p>}
            </li>)}
          </ul> : <p className="mt-2 text-muted-foreground">Please review your package details with the programme team if anything is unclear.</p>}
        </div>
        {(quotation.preferred_package_name || quotation.preferred_fee_plan_name) && <div className="rounded-lg border bg-muted/20 p-4 space-y-1">
          <h3 className="font-semibold">Your original preference</h3>
          <p>{quotation.preferred_package_name || 'Package'}{quotation.preferred_fee_plan_name ? ` — ${quotation.preferred_fee_plan_name}` : ''}</p>
          {quotation.preferred_total_amount_subunit != null && quotation.preferred_currency &&
            <p>{formatMoney(quotation.preferred_total_amount_subunit, quotation.preferred_currency)}</p>}
          {(quotation.preferred_package_name && quotation.package_name !== quotation.preferred_package_name ||
            quotation.preferred_total_amount_subunit != null && quotation.preferred_total_amount_subunit !== quotation.gross_total_subunit) &&
            <p className="font-medium text-amber-700">This offer differs from your requested package or payment arrangement. Review the final terms carefully and contact the programme team if the change is unclear.</p>}
        </div>}
        <div className="rounded-lg border p-4 space-y-2">
          <h3 className="font-semibold">Your fees</h3>
          <div className="flex justify-between gap-4"><span>Programme fee</span><b>{formatMoney(quotation.gross_total_subunit, quotation.currency)}</b></div>
          {quotation.scholarship_subunit > 0 && <div className="flex justify-between gap-4"><span>Approved scholarship support</span><b>− {formatMoney(quotation.scholarship_subunit, quotation.currency)}</b></div>}
          <div className="flex justify-between gap-4 border-t pt-3 text-base"><span className="font-semibold">Total to pay</span><b>{formatMoney(quotation.payable_total_subunit, quotation.currency)}</b></div>
        </div>
        <div>
          <h3 className="font-semibold">Payment schedule</h3>
          <ul className="mt-2 divide-y rounded-lg border">
            {quotation.installments.map(line => <li key={line.sequence_number} className="flex flex-wrap justify-between gap-2 p-3">
              <span>Instalment {line.sequence_number}{line.due_date ? ` · Due ${localDate(line.due_date)}` : ''}{line.description && <span className="block text-muted-foreground">{line.description}</span>}</span>
              <b>{formatMoney(line.amount_subunit, quotation.currency)}</b>
            </li>)}
          </ul>
        </div>
        {quotation.status === 'offered' && !expired && !paymentUrl && <>
          <label className="flex items-start gap-3 rounded-lg border p-4">
            <input type="checkbox" className="mt-1" checked={agreed} disabled={busy} onChange={e => setAgreed(e.target.checked)}/>
            <span>I have reviewed and accept the package, fee amount and instalment schedule shown above. I understand that accepting creates payment invoices, but payment is a separate step.</span>
          </label>
          <Button type="button" disabled={!agreed || busy} onClick={accept}>{busy ? 'Accepting quotation…' : 'Accept quotation and continue to payment'}</Button>
        </>}
        {quotation.status === 'accepted' && !paymentUrl && <p className="rounded-md border p-3">You have already accepted this quotation. Please use your private payment link or contact the programme team for assistance.</p>}
        {paymentUrl && <p className="rounded-md border p-3">Quotation accepted. <a className="font-semibold underline" href={paymentUrl}>Continue to secure payment</a>. Keep this link private.</p>}
        <p className="text-xs text-muted-foreground">Need help understanding these terms? Contact the programme team before accepting. Do not share your application status link.</p>
      </>}
    </CardContent>
  </Card>
}
