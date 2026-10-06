import { NextRequest, NextResponse } from 'next/server'
const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'
const COOKIE = 'rdp_portal_token'

export async function POST(request: NextRequest) {
  const { email, password } = await request.json().catch(() => ({})) as { email?: string; password?: string }
  if (!email || !password) return NextResponse.json({ error: 'Email and password are required.' }, { status: 400 })
  const form = new URLSearchParams({ username: email, password })
  let auth: Response
  try {
    auth = await fetch(`${BACKEND_URL}/api/v1/auth/rdp-login`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: form.toString() })
  } catch {
    return NextResponse.json({ error: 'Could not reach the backend server.' }, { status: 502 })
  }
  if (!auth.ok) {
    const data = await auth.json().catch(() => ({})) as { detail?: string }
    return NextResponse.json({ error: data.detail ?? 'Login failed.' }, { status: auth.status })
  }
  const { access_token } = await auth.json() as { access_token: string }
  // Verify this account is an RDP participant before issuing the RDP cookie.
  const check = await fetch(`${BACKEND_URL}/api/v1/rdp/portal/dashboard`, { headers: { Authorization: `Bearer ${access_token}` } })
  if (!check.ok) return NextResponse.json({ error: 'This account does not have programme-participant access.' }, { status: 403 })
  const res = NextResponse.json({ ok: true })
  res.cookies.set(COOKIE, access_token, { httpOnly: true, secure: process.env.NODE_ENV === 'production', sameSite: 'strict', path: '/', maxAge: 60 * 60 * 24 })
  return res
}
