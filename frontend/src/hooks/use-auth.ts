'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'

export interface AdminUser {
  id: number
  email: string
  is_active: boolean
  is_admin: boolean
}

export function useAuth() {
  const [user, setUser] = useState<AdminUser | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    fetch('/api/auth/me')
      .then(async (response) => {
        if (!response.ok) return null
        const data = await response.json() as AdminUser
        return data.is_admin ? data : null
      })
      .then(async (data: AdminUser | null) => {
        if (!data) {
          await fetch('/api/auth/logout', { method: 'POST' })
          router.replace('/admin/login')
          router.refresh()
        }
        setUser(data)
        setLoading(false)
      })
      .catch(async () => {
        await fetch('/api/auth/logout', { method: 'POST' }).catch(() => undefined)
        setLoading(false)
        router.replace('/admin/login')
      })
  }, [router])

  const logout = useCallback(async () => {
    await fetch('/api/auth/logout', { method: 'POST' })
    router.push('/admin/login')
    router.refresh()
  }, [router])

  return { user, loading, logout }
}
