import { AlertCircle } from 'lucide-react'
export function ApiErrorAlert({message}:{message:string|null|undefined}){
 if(!message)return null
 return <div role="alert" aria-live="assertive" className="flex gap-3 rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true"/><p className="whitespace-pre-wrap break-words">{message}</p></div>
}
