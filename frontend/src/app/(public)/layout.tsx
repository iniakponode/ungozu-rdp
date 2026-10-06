import Link from 'next/link'
import { RDPSubnav } from '@/components/rdp/rdp-subnav'

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return <div><RDPSubnav />{children}<div className="border-t border-border/60 bg-muted/20"><div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-5 gap-y-2 px-4 py-5 text-xs text-muted-foreground sm:px-6 lg:px-8"><span>Ungozu R & D Researcher Development Programme</span><a href={process.env.NEXT_PUBLIC_MAIN_SITE_URL ?? "https://iniakpothompson.com"} className="hover:text-foreground">Main website</a><Link href="/privacy" className="hover:text-foreground">Programme privacy</Link><Link href="/terms" className="hover:text-foreground">Programme terms</Link><a href="mailto:iniakpothompson@ndu.edu.ng" className="hover:text-foreground">Contact programme director</a></div></div></div>
}
