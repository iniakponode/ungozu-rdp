import ScholarshipClient from './scholarship-client'
export default async function ScholarshipPage({searchParams}:{searchParams:Promise<{ref?:string;token?:string}>}){const p=await searchParams;return <ScholarshipClient initialRef={p.ref??''} initialToken={p.token??''}/>}
