import { NextRequest, NextResponse } from 'next/server'

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])

/** Reject browser mutations that did not originate from this site. */
export function rejectCrossSiteMutation(request: NextRequest): NextResponse | null {
  if (SAFE_METHODS.has(request.method)) return null

  const origin = request.headers.get('origin')
  const forwardedHost = request.headers.get('x-forwarded-host')?.split(',')[0]?.trim()
  const host = forwardedHost || request.headers.get('host')

  if (!origin || !host) {
    return NextResponse.json({ error: 'Invalid request origin.' }, { status: 403 })
  }

  try {
    if (new URL(origin).host !== host) {
      return NextResponse.json({ error: 'Invalid request origin.' }, { status: 403 })
    }
  } catch {
    return NextResponse.json({ error: 'Invalid request origin.' }, { status: 403 })
  }

  return null
}
