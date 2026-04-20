// hooks/useAuth.ts - Authentication hook
import { useState, useCallback } from 'react'
import { authService, type LoginRequest, type RegisterRequest } from '@/services/auth'
import { useRouter } from 'next/navigation'

export function useAuth() {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<Error | null>(null)
    const router = useRouter()

    const login = useCallback(async (credentials: LoginRequest) => {
        setLoading(true)
        setError(null)
        try {
            const response = await authService.login(credentials)
            router.push('/dashboard')
            return response
        } catch (err) {
            const error = err instanceof Error ? err : new Error(String(err))
            setError(error)
            throw error
        } finally {
            setLoading(false)
        }
    }, [router])

    const register = useCallback(async (userData: RegisterRequest) => {
        setLoading(true)
        setError(null)
        try {
            const response = await authService.register(userData)
            router.push('/dashboard')
            return response
        } catch (err) {
            const error = err instanceof Error ? err : new Error(String(err))
            setError(error)
            throw error
        } finally {
            setLoading(false)
        }
    }, [router])

    const logout = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            await authService.logout()
            router.push('/login')
        } catch (err) {
            const error = err instanceof Error ? err : new Error(String(err))
            setError(error)
        } finally {
            setLoading(false)
        }
    }, [router])

    return {
        login,
        register,
        logout,
        isAuthenticated: authService.isAuthenticated(),
        loading,
        error,
    }
}
