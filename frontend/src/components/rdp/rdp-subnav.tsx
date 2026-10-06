'use client'

import Image from 'next/image'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LogIn } from 'lucide-react'
import { cn } from '@/lib/utils'

const MAIN_SITE = process.env.NEXT_PUBLIC_MAIN_SITE_URL ?? 'https://iniakpothompson.com'

const links = [
  { href: '/', label: 'Overview' },
  { href: '/programme', label: 'Programme' },
  { href: '/mentor', label: 'Mentor' },
  { href: '/fees', label: 'Fees' },
  { href: '/faq', label: 'FAQ' },
  { href: '/status', label: 'Application status' },
]

export function RDPSubnav() {
  const pathname = usePathname()
  return (
    <div className="border-b border-border/60 bg-card/70">
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="flex min-w-0 items-center gap-3">
          <Image src="/rdp-logo.png" alt="Ungozu R & D" width={42} height={42} className="h-10 w-10 rounded-md object-contain" />
          <div className="hidden min-w-0 sm:block">
            <p className="truncate text-sm font-semibold text-foreground">Ungozu R & D</p>
            <p className="truncate text-[11px] text-muted-foreground">Researcher Development Programme</p>
          </div>
        </Link>
        <nav className="ml-auto hidden items-center gap-1 xl:flex" aria-label="Programme navigation">
          <a href={MAIN_SITE} className="rounded-md px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent">Main website</a>
          {links.map((item) => (
            <Link key={item.href} href={item.href} className={cn('rounded-md px-3 py-1.5 text-xs transition-colors hover:bg-accent', pathname === item.href ? 'bg-accent font-medium text-foreground' : 'text-muted-foreground')}>
              {item.label}
            </Link>
          ))}
          <Link href="/apply" className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground">Apply</Link>
          <Link href="/login" className="inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent"><LogIn className="h-3.5 w-3.5"/>Participant login</Link>
        </nav>
        <div className="ml-auto flex gap-2 xl:hidden">
          <Link href="/apply" className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground">Apply</Link>
          <Link href="/login" className="rounded-md border border-border px-3 py-1.5 text-xs">Login</Link>
        </div>
      </div>
    </div>
  )
}
