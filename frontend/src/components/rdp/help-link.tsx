import Link from 'next/link'
import { CircleHelp } from 'lucide-react'
const locations:Record<string,string>={builder:'section-03',curriculum:'section-04',assessments:'section-05',fees:'section-06',applications:'section-08',payments:'section-09',participants:'section-10',certificates:'section-11',content:'section-12',email:'section-13'}
export function AdminHelpLink({topic='builder',label='Help & walkthrough'}:{topic?:string;label?:string}) {
 return <Link href={'/admin/help#'+(locations[topic]??'section-01')} className="inline-flex items-center gap-1 text-sm font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-primary"><CircleHelp className="h-4 w-4" aria-hidden="true"/>{label}</Link>
}
