import { NextRequest, NextResponse } from 'next/server'
import { rejectCrossSiteMutation } from '@/lib/server/request-security'

const COOKIE_NAME = 'admin_token'

export async function POST(request: NextRequest) {
  const originError = rejectCrossSiteMutation(request)
  if (originError) return originError

  const response = NextResponse.json({ ok: true })
  response.cookies.set(COOKIE_NAME, '', {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    path: '/',
    maxAge: 0,
  })
  return response
}
