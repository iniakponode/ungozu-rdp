import { Badge } from '@/components/ui/badge'

export function formatMoney(subunit: number, currency: string) {
  return new Intl.NumberFormat('en', { style: 'currency', currency, maximumFractionDigits: currency === 'NGN' ? 0 : 2 }).format(subunit / 100)
}

export function ProgrammeStatus({ status }: { status: string }) {
  const label = status.replaceAll('_', ' ')
  return <Badge variant="outline" className="capitalize">{label}</Badge>
}

export function RDPSectionHeading({ eyebrow, title, text }: { eyebrow?: string; title: string; text?: string }) {
  return <div className="max-w-3xl">
    {eyebrow && <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">{eyebrow}</p>}
    <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h2>
    {text && <p className="mt-3 text-sm leading-6 text-muted-foreground sm:text-base">{text}</p>}
  </div>
}
