import PaymentClient from './payment-client'
export default async function PaymentPage({searchParams}:{searchParams:Promise<{ref?:string;token?:string}>}){const p=await searchParams;return <PaymentClient refCode={p.ref??''} paymentToken={p.token??''}/>}
