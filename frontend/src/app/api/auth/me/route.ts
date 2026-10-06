import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'
const COOKIE_NAME = 'admin_token'

export async function GET(request: NextRequest) {
  const token = request.cookies.get(COOKIE_NAME)?.value

  if (!token) {
    return NextResponse.json({ error: 'Not authenticated.' }, { status: 401 })
  }

  let backendRes: Response
  try {
    backendRes = await fetch(`${BACKEND_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
  } catch {
    return NextResponse.json({ error: 'Could not reach the backend server.' }, { status: 502 })
  }

  if (!backendRes.ok) {
    return NextResponse.json({ error: 'Unauthorized.' }, { status: 401 })
  }

  return NextResponse.json(await backendRes.json())
}
