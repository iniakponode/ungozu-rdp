import SetPasswordClient from './set-password-client'
export default async function SetPasswordPage({searchParams}:{searchParams:Promise<{token?:string}>}){const p=await searchParams;return <SetPasswordClient token={p.token??''}/>}
