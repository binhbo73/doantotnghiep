'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthContext } from '@/context'

interface ProtectedRouteProps {
    children: React.ReactNode
    requiredRole?: string // 'admin', 'user', etc. Optional
}

/**
 * ProtectedRoute - Wrapper component to protect dashboard and child routes
 * Redirects to login if not authenticated
 * Can optionally check for specific roles
 */
export function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
    const router = useRouter()
    const { isAuthenticated, isLoading, user } = useAuthContext()

    useEffect(() => {
        // If still loading, don't do anything yet
        if (isLoading) return

        // If not authenticated, redirect to login
        if (!isAuthenticated) {
            router.push('/login?redirect=' + encodeURIComponent(window.location.pathname))
            return
        }

        // If role is required, check it
        if (requiredRole && user?.role !== requiredRole) {
            // Redirect to unauthorized page or dashboard
            router.push('/dashboard')
        }
    }, [isAuthenticated, isLoading, requiredRole, user?.role, router])

    // Show loading state while checking auth
    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-center">
                    <div className="inline-block">
                        <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                    </div>
                    <p className="mt-4 text-gray-600">Đang xác thực...</p>
                </div>
            </div>
        )
    }

    // Show nothing while not authenticated (middleware handles redirect)
    if (!isAuthenticated) {
        return null
    }

    // If role check failed, show nothing
    if (requiredRole && user?.role !== requiredRole) {
        return null
    }

    // User is authenticated and has permission, render children
    return <>{children}</>
}
