import { NextRequest, NextResponse } from 'next/server'
import { rejectCrossSiteMutation } from '@/lib/server/request-security'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'
const COOKIE_NAME = 'admin_token'
const COOKIE_MAX_AGE = 60 * 60 * 24 // 24 hours

export async function POST(request: NextRequest) {
  const originError = rejectCrossSiteMutation(request)
  if (originError) return originError

  let email: string
  let password: string

  try {
    const body = await request.json()
    email = body.email
    password = body.password
  } catch {
    return NextResponse.json({ error: 'Invalid request body.' }, { status: 400 })
  }

  if (!email || !password) {
    return NextResponse.json({ error: 'Email and password are required.' }, { status: 400 })
  }

  // FastAPI expects OAuth2PasswordRequestForm (x-www-form-urlencoded)
  const formData = new URLSearchParams()
  formData.append('username', email)
  formData.append('password', password)

  let backendRes: Response
  try {
    backendRes = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    })
  } catch {
    return NextResponse.json({ error: 'Could not reach the backend server.' }, { status: 502 })
  }

  if (!backendRes.ok) {
    const data = await backendRes.json().catch(() => ({}))
    const detail = (data as { detail?: string }).detail ?? 'Login failed.'
    return NextResponse.json({ error: detail }, { status: backendRes.status })
  }

  const { access_token } = await backendRes.json() as { access_token: string }

  const response = NextResponse.json({ ok: true })
  response.cookies.set(COOKIE_NAME, access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    path: '/',
    maxAge: COOKIE_MAX_AGE,
  })
  return response
}
