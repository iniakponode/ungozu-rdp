import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'
const COOKIE = 'rdp_portal_token'

async function handler(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const token = request.cookies.get(COOKIE)?.value
  if (!token) return NextResponse.json({ detail: 'Not authenticated' }, { status: 401 })
  const { path } = await params
  const url = new URL(`/api/v1/rdp/portal/${path.join('/')}`, BACKEND_URL)
  request.nextUrl.searchParams.forEach((value, key) => url.searchParams.set(key, value))
  const headers: HeadersInit = { Authorization: `Bearer ${token}` }
  const contentType = request.headers.get('content-type')
  if (contentType) headers['Content-Type'] = contentType
  const body = request.method === 'GET' || request.method === 'HEAD' ? null : await request.text() || null
  try {
    const r = await fetch(url.toString(), { method: request.method, headers, body })
    const h = new Headers(); const ct = r.headers.get('content-type'); if (ct) h.set('content-type', ct)
    return new NextResponse(r.body, { status: r.status, headers: h })
  } catch {
    return NextResponse.json({ detail: 'Could not reach the backend server.' }, { status: 502 })
  }
}
export const GET = handler
export const POST = handler
export const PUT = handler
export const PATCH = handler
