import { NextRequest, NextResponse } from 'next/server'
import { rejectCrossSiteMutation } from '@/lib/server/request-security'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:8010'

async function handler(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params
  // Payment-provider webhooks are server-to-server POSTs without a browser Origin.
  // Preserve ONLY the exact existing webhook paths; FastAPI verifies providers.
  const webhook = request.method === 'POST' &&
    ((path.length === 3 && path[0] === 'payments' && path[1] === 'webhooks' &&
      (path[2] === 'stripe' || path[2] === 'paystack')) ||
     (path.length === 2 && path[0] === 'payments' && path[1] === 'webhook'))
  if (!webhook) {
    const originError = rejectCrossSiteMutation(request)
    if (originError) return originError
  }
  const url = new URL(`/api/v1/rdp/public/${path.join('/')}`, BACKEND_URL)
  request.nextUrl.searchParams.forEach((value, key) => url.searchParams.set(key, value))

  const headers: HeadersInit = {}
  const contentType = request.headers.get('content-type')
  if (contentType) headers['Content-Type'] = contentType
  // Signature verification occurs in FastAPI; forward only webhook signature headers.
  if (webhook) {
    for (const name of ['stripe-signature', 'x-paystack-signature']) {
      const signature = request.headers.get(name)
      if (signature) headers[name] = signature
    }
  }

  let body: BodyInit | null = null
  if (webhook) {
    // Keep the exact bytes providers signed; text decoding could change the payload.
    body = await request.arrayBuffer()
  } else if (request.method !== 'GET' && request.method !== 'HEAD') {
    body = await request.text() || null
  }

  try {
    const r = await fetch(url.toString(), { method: request.method, headers, body })
    const h = new Headers()
    const ct = r.headers.get('content-type'); if (ct) h.set('content-type', ct)
    // Never cache private applicant, quotation, invoice or payment responses.
    if (['quotation', 'quotations', 'application-status', 'payment-summary', 'payment-providers', 'payments'].includes(path[0])) {
      h.set('Cache-Control', 'private, no-store, max-age=0')
      h.set('Pragma', 'no-cache')
    }
    return new NextResponse(r.body, { status: r.status, headers: h })
  } catch {
    return NextResponse.json({ detail: 'Could not reach the backend server.' }, { status: 502 })
  }
}

export const GET = handler
export const POST = handler
export const PUT = handler
export const PATCH = handler
