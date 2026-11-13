import { NextRequest, NextResponse } from 'next/server'
import { rejectCrossSiteMutation } from '@/lib/server/request-security'

// Route through the authenticated BFF. Never expose session tokens to browser JavaScript.
const BACKEND_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:8010'
const allowed = new Set(['GET', 'POST', 'PUT'])

type Params = { params: Promise<{ path: string[] }> }
async function handler(request: NextRequest, { params }: Params) {
  if (!allowed.has(request.method)) return NextResponse.json({ detail: 'Method not allowed' }, { status: 405 })
  const originError = rejectCrossSiteMutation(request)
  if (originError) return originError
  const segments = (await params).path
  const admin = segments[0] === 'admin'
  const participant = segments[0] === 'mine'
  // Exact route/method allowlist: prevent accidental forwarding of future endpoints.
  const numericId = (value: string | undefined) => !!value && /^[1-9][0-9]*$/.test(value)
  const list = request.method === 'GET' && segments.length === 1 && (admin || participant)
  const download = request.method === 'GET' && segments.length === 3 &&
    (admin || participant) && numericId(segments[1]) && segments[2] === 'download'
  const upload = request.method === 'POST' && admin &&
    segments.length === 2 && segments[1] === 'upload'
  const publish = request.method === 'PUT' && admin &&
    segments.length === 3 && numericId(segments[1]) && segments[2] === 'publish'
  if (!list && !download && !upload && !publish) {
    return NextResponse.json({ detail: 'Not found' }, { status: 404 })
  }
  const token = request.cookies.get(admin ? 'admin_token' : 'rdp_portal_token')?.value
  if (!token) return NextResponse.json({ detail: 'Not authenticated' }, { status: 401 })
  const url = new URL(`/api/v1/rdp/learning-resources/${segments.join('/')}`, BACKEND_URL)
  request.nextUrl.searchParams.forEach((value, key) => url.searchParams.append(key, value))
  const headers = new Headers({ Authorization: `Bearer ${token}` })
  const contentType = request.headers.get('content-type')
  if (contentType) headers.set('Content-Type', contentType)
  // The FastAPI endpoint expects raw DOCX bytes, not multipart/form-data.
  if (upload && contentType && !contentType.toLowerCase().startsWith(
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  )) {
    return NextResponse.json({ detail: 'Expected DOCX content type' }, { status: 415 })
  }
  if (upload && Number(request.headers.get('content-length') ?? 0) > 15 * 1024 * 1024) {
    return NextResponse.json({ detail: 'DOCX exceeds 15 MiB' }, { status: 413 })
  }
  try {
    let body: ArrayBuffer | undefined
    if (upload) {
      // Enforce the cap while reading. Clients can omit Content-Length.
      const reader = request.body?.getReader()
      if (!reader) return NextResponse.json({ detail: 'Empty upload' }, { status: 400 })
      const chunks: Uint8Array[] = []
      let total = 0
      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          total += value.byteLength
          if (total > 15 * 1024 * 1024) {
            await reader.cancel()
            return NextResponse.json({ detail: 'DOCX exceeds 15 MiB' }, { status: 413 })
          }
          chunks.push(value)
        }
      } finally {
        reader.releaseLock()
      }
      if (total === 0) return NextResponse.json({ detail: 'Empty upload' }, { status: 400 })
      body = new ArrayBuffer(total)
      const bytes = new Uint8Array(body)
      let offset = 0
      for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength }
    } else if (request.method !== 'GET') {
      body = await request.arrayBuffer()
    }
    const result = await fetch(url, { method: request.method, headers, body, cache: 'no-store', redirect:'manual' })
    const responseHeaders = new Headers()
    for (const key of ['content-type', 'content-disposition']) {
      const value = result.headers.get(key)
      if (value) responseHeaders.set(key, value)
    }
    responseHeaders.set('Cache-Control', 'private, no-store')
    responseHeaders.set('X-Content-Type-Options', 'nosniff')
    return new NextResponse(result.body, { status: result.status, headers: responseHeaders })
  } catch {
    return NextResponse.json({ detail: 'Could not reach learning resources API.' }, { status: 502 })
  }
}
export const GET = handler
export const POST = handler
export const PUT = handler
