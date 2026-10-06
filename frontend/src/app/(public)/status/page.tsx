import StatusClient from './status-client'
export default async function StatusPage({searchParams}:{searchParams:Promise<{ref?:string;token?:string}>}){const p=await searchParams;return <StatusClient initialRef={p.ref??''} initialToken={p.token??''}/>}
