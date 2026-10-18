'use client'

import type { Catalogue } from '@/lib/rdp-catalogue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatMoney } from '@/components/rdp/rdp-ui'

type Props = {
  catalogue: Catalogue
  packageId: number | null
  planId: number | null
  onPackageChange: (id: number) => void
  onPlanChange: (id: number) => void
}

export function ApplicationPackagePreference({catalogue, packageId, planId, onPackageChange, onPlanChange}: Props) {
  const plansFor = (id: number) => catalogue.fee_plans.filter(plan => plan.package_id === id)
  const available = catalogue.packages.filter(pkg => plansFor(pkg.id).length > 0)
  const selectedPackage = available.find(pkg => pkg.id === packageId)
  const choices = selectedPackage ? plansFor(selectedPackage.id) : []
  const selectedPlan = choices.find(plan => plan.id === planId)
  if (available.length === 0) return null

  return <Card id="package-preference">
    <CardHeader>
      <CardTitle className="text-lg">Choose your preferred mentoring package</CardTitle>
      <p className="text-sm text-muted-foreground">Compare the support included in each package, then choose your preferred payment arrangement. Your choice will be considered during admission; it does not reserve a place or require payment now.</p>
    </CardHeader>
    <CardContent className="space-y-5">
      <fieldset className="space-y-3">
        <legend className="mb-2 font-medium">Mentoring package</legend>
        <div className="grid gap-3 md:grid-cols-2">
          {available.map(pkg => {
            const cheapest = [...plansFor(pkg.id)].sort((a, b) => a.total_amount_subunit-b.total_amount_subunit)[0]
            return <label key={pkg.id} className={`block cursor-pointer rounded-xl border p-4 ${packageId===pkg.id?'border-primary ring-2 ring-primary/20':''}`}>
              <span className="flex items-start gap-3">
                <input type="radio" name="preferred-package" value={pkg.id} checked={packageId===pkg.id}
                  onChange={() => onPackageChange(pkg.id)} required className="mt-1"/>
                <span className="space-y-2">
                  <span className="block font-semibold">{pkg.name}</span>
                  {pkg.description && <span className="block text-sm text-muted-foreground">{pkg.description}</span>}
                  {cheapest && <span className="block text-sm">From {formatMoney(cheapest.total_amount_subunit,cheapest.currency)}</span>}
                  {pkg.entitlements.length>0 && <span className="block text-sm text-muted-foreground">
                    {pkg.entitlements.slice(0,7).map(e => <span className="block" key={e.code}>• {e.name}{e.quantity!=null?` — ${e.quantity} ${e.unit??''}`:''}</span>)}
                    {pkg.entitlements.length>7 && <span className="block">+ {pkg.entitlements.length-7} more included benefits</span>}
                  </span>}
                </span>
              </span>
            </label>
          })}
        </div>
      </fieldset>
      {selectedPackage && <fieldset className="space-y-3">
        <legend className="font-medium">Preferred payment arrangement</legend>
        {choices.map(plan => <label key={plan.id} className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 ${planId===plan.id?'border-primary ring-2 ring-primary/20':''}`}>
          <input type="radio" name="preferred-fee-plan" value={plan.id} checked={planId===plan.id}
            onChange={() => onPlanChange(plan.id)} required className="mt-1"/>
          <span className="flex-1">
            <span className="block font-medium">{plan.name} — {formatMoney(plan.total_amount_subunit,plan.currency)}</span>
            <span className="block text-sm text-muted-foreground">{plan.installment_count} {plan.installment_count===1?'payment':'instalments'} · {plan.region.replaceAll('_',' ')}{plan.description?` · ${plan.description}`:''}</span>
            {plan.installments.length>1 && <span className="mt-1 block text-xs text-muted-foreground">
              {plan.installments.map(x => <span key={x.sequence_number} className="block">Instalment {x.sequence_number}: {formatMoney(x.amount_subunit,plan.currency)} · {x.due_offset_days===0?'due on offer date':`due ${x.due_offset_days} days after the offer date`}</span>)}
            </span>}
          </span>
        </label>)}
      </fieldset>}
      {selectedPlan && <div className="rounded-lg border bg-muted/20 p-4" role="status">
        <p className="text-xs uppercase tracking-wider text-muted-foreground">Your preferred arrangement</p>
        <p className="mt-1 font-semibold">{selectedPackage?.name} · {selectedPlan.name}</p>
        <p className="text-lg font-semibold">{formatMoney(selectedPlan.total_amount_subunit,selectedPlan.currency)}</p>
        <p className="text-xs text-muted-foreground">No payment is due at application. Your final offer may differ if eligibility, scholarship support or package availability changes. You will review and accept the final quotation before paying.</p>
      </div>}
    </CardContent>
  </Card>
}
