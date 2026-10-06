import type { Metadata } from 'next'
import { LoginForm } from './_components/login-form'

export const metadata: Metadata = { title: 'Admin — Sign In' }

export default function AdminLoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Admin Sign In</h1>
          <p className="mt-1 text-sm text-muted-foreground">Sign in to manage your content.</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-6">
          <LoginForm />
        </div>
      </div>
    </div>
  )
}
