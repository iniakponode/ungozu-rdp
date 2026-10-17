import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'

async function handler(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params
  const url = new URL(`/api/v1/rdp/public/${path.join('/')}`, BACKEND_URL)
  request.nextUrl.searchParams.forEach((value, key) => url.searchParams.set(key, value))

  const headers: HeadersInit = {}
  const contentType = request.headers.get('content-type')
  if (contentType) headers['Content-Type'] = contentType

  let body: BodyInit | null = null
  if (request.method !== 'GET' && request.method !== 'HEAD') body = await request.text() || null

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
