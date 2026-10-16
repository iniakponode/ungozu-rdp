'use client'
import {Button} from '@/components/ui/button'
export function CertificatePrint(){return <Button onClick={()=>window.print()}>Print / Save PDF</Button>}
