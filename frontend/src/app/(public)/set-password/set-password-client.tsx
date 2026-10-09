'use client'

import { FormEvent, useState } from 'react'
import Link from 'next/link'
import { setRdpPassword } from '@/lib/rdp-api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { PasswordInput } from '@/components/ui/password-input'

export default function SetPasswordClient({ token }: { token: string }) {
  const [pw, setPw] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (pw.length < 8) {
      setError('Password must be at least 8 characters long.')
      return
    }
    if (pw !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      await setRdpPassword(token, pw)
      setDone(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not set password')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl px-4 py-16 sm:px-6">
      <Card>
        <CardHeader>
          <CardTitle>{done ? 'Password updated' : 'Set participant portal password'}</CardTitle>
        </CardHeader>
        <CardContent>
          {done ? (
            <div className="space-y-4 text-sm text-muted-foreground">
              <p>Your password has been set successfully.</p>
              <Button asChild>
                <Link href="/login">Sign in to the participant portal</Link>
              </Button>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-4">
              <div>
                <Label htmlFor="new-password">New password</Label>
                <PasswordInput
                  id="new-password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  value={pw}
                  onChange={(e) => setPw(e.target.value)}
                />
                <p className="mt-1 text-xs text-muted-foreground">Minimum 8 characters.</p>
              </div>
              <div>
                <Label htmlFor="confirm-password">Confirm password</Label>
                <PasswordInput
                  id="confirm-password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                />
                {confirm && pw !== confirm && (
                  <p className="mt-1 text-xs text-destructive">Passwords do not match.</p>
                )}
              </div>
              {!token && <p className="text-sm text-destructive">This password-setup link is incomplete.</p>}
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button disabled={busy || !token}>{busy ? 'Updating…' : 'Set password'}</Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
