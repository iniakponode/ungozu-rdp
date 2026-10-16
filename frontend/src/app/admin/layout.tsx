'use client'

import { usePathname } from 'next/navigation'
import { useAuth } from '@/hooks/use-auth'
import { RDPAdminNav } from '@/components/rdp-admin-nav'

type Props = { children: React.ReactNode }

/**
 * Do not mount the admin authentication hook on the login route.
 * The hook logs out unauthenticated visitors; when mounted on the login page,
 * its outstanding logout call can race with a successful sign-in and delete
 * the newly issued admin cookie.
 */
export default function AdminLayout({ children }: Props) {
  const pathname = usePathname()
  if (pathname === '/admin/login') return <>{children}</>
  return <AuthenticatedAdminLayout>{children}</AuthenticatedAdminLayout>
}

function AuthenticatedAdminLayout({ children }: Props) {
  const { user, loading, logout } = useAuth()
  if (loading || !user?.is_admin) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Verifying administrator access…
      </div>
    )
  }
  return (
    <div className="flex min-h-screen bg-background">
      <RDPAdminNav onLogout={logout} />
      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</div>
      </main>
    </div>
  )
}
