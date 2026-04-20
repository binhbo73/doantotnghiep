'use client'

import { useRouter } from 'next/navigation'
import { useAuthContext } from '@/context'
import { useEffect } from 'react'

/**
 * Hook để kiểm tra bảo vệ route
 * Tự động redirect nếu chưa xác thực hoặc không có quyền
 * 
 * @param requiredRole - (Optional) Role cần thiết, ví dụ 'admin'
 * @returns { isProtected: boolean, isLoading: boolean }
 * 
 * @example
 * ```tsx
 * export default function AdminPage() {
 *     const { isProtected } = useProtectedRoute('admin')
 *     
 *     if (!isProtected) return null
 *     
 *     return <AdminDashboard />
 * }
 * ```
 */
export function useProtectedRoute(requiredRole?: string) {
    const router = useRouter()
    const { isAuthenticated, isLoading, user } = useAuthContext()

    useEffect(() => {
        if (isLoading) return

        // Redirect if not authenticated
        if (!isAuthenticated) {
            router.push('/login')
            return
        }

        // Check role if required
        if (requiredRole && user?.role !== requiredRole) {
            router.push('/dashboard')
            return
        }
    }, [isAuthenticated, isLoading, requiredRole, user?.role, router])

    const isProtected = isAuthenticated && (!requiredRole || user?.role === requiredRole)

    return {
        isProtected,
        isLoading,
        user,
    }
}

/**
 * Hook để kiểm tra quyền admin
 * Wrapper tiện lợi cho useProtectedRoute('admin')
 * 
 * @returns { isAdmin: boolean, isLoading: boolean }
 * 
 * @example
 * ```tsx
 * const { isAdmin } = useAdminCheck()
 * if (!isAdmin) return <Unauthorized />
 * ```
 */
export function useAdminCheck() {
    const { isProtected, isLoading, user } = useProtectedRoute('admin')

    return {
        isAdmin: isProtected,
        isLoading,
        user,
    }
}

/**
 * Hook để lấy user info hiện tại
 * @returns User object hoặc null nếu chưa đăng nhập
 */
export function useCurrentUser() {
    const { user, isAuthenticated } = useAuthContext()

    if (!isAuthenticated || !user) {
        return null
    }

    return user
}
