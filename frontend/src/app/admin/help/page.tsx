import Link from 'next/link'
import { BookOpen, ArrowRight } from 'lucide-react'
import { adminHelpSections } from '@/lib/rdp-admin-help-content'
import { AdminHelpSearch } from '@/components/rdp/admin-help-search'
export const metadata = {title:'Administrator Help | Ungozu R&D'}
export default function AdministratorHelpPage(){
 return <div id="top" className="space-y-6">
  <div className="space-y-2"><div className="flex items-center gap-2 text-primary"><BookOpen className="h-5 w-5"/><span className="text-sm font-semibold">Administrator handbook</span></div><h1 className="text-3xl font-bold">Administration help and walkthroughs</h1><p className="text-sm text-muted-foreground">The online handbook explains each workflow and links you directly to its administration page. Select an entry below, or search the instructions. Check policies and production data before publishing, taking payment or issuing a certificate.</p></div>
  <AdminHelpSearch sections={adminHelpSections}/>
  <nav aria-label="Help contents" className="grid gap-2 md:grid-cols-2">{adminHelpSections.map(s=><a key={s.id} className="rounded-lg border p-3 text-sm hover:bg-accent focus-visible:outline-2 focus-visible:outline-primary" href={'#'+s.id}>{s.title}</a>)}</nav>
  {adminHelpSections.map(s=><section id={s.id} key={s.id} className="scroll-mt-6 rounded-xl border bg-card p-5 sm:p-6"><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start"><h2 className="text-xl font-semibold">{s.title}</h2><Link className="inline-flex shrink-0 items-center gap-1 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90" href={s.href}>{s.linkLabel}<ArrowRight className="h-4 w-4"/></Link></div><div className="mt-4 space-y-3 text-sm leading-relaxed">{s.blocks.map((b,i)=>b.kind==='subheading'?<h3 key={i} className="pt-3 text-base font-semibold">{b.text}</h3>:b.kind==='bullet'?<p key={i} className="ml-5 list-item list-disc">{b.text}</p>:b.kind==='note'?<aside key={i} className="rounded-md border-l-4 border-primary bg-muted/40 p-3">{b.text}</aside>:b.kind==='table'?<div key={i} className="overflow-x-auto"><table className="w-full border-collapse text-left text-sm"><tbody>{(b.rows??[]).map((r,j)=><tr key={j} className="border-b">{r.map((v,k)=>j===0?<th scope="col" key={k} className="p-2 font-semibold">{v}</th>:<td key={k} className="p-2 align-top">{v}</td>)}</tr>)}</tbody></table></div>:<p key={i}>{b.text}</p>)}</div><a className="mt-5 inline-block text-sm text-primary underline" href="#top">Back to top</a></section>)}
  <p className="text-xs text-muted-foreground">The handbook is operational guidance. The application's server-side business rules remain authoritative. No page in this help section changes programme data.</p>
 </div>
}
