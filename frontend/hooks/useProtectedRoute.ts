'use client'

import { useRouter } from 'next/navigation'
import { useAuthContext } from '@/context'
import { useEffect } from 'react'
import { useRBAC } from './useRBAC'

/**
 * Hook để kiểm tra bảo vệ route
 * Tự động redirect nếu chưa xác thực hoặc không có quyền
 * 
 * @param requiredPermissions - (Optional) permission codes required for the route
 * @returns { isProtected: boolean, isLoading: boolean }
 * 
 * @example
 * ```tsx
 * export default function PermissionedPage() {
 *     const { isProtected } = useProtectedRoute(['system_admin'])
 *     
 *     if (!isProtected) return null
 *     
 *     return <PermissionedDashboard />
 * }
 * ```
 */
export function useProtectedRoute(requiredPermissions?: string[]) {
    const router = useRouter()
    const { isAuthenticated, isLoading, user } = useAuthContext()
    const { hasAnyPermission } = useRBAC()
    const hasRequiredPermissions = !requiredPermissions || requiredPermissions.length === 0 || hasAnyPermission(requiredPermissions)

    useEffect(() => {
        if (isLoading) return

        // Redirect if not authenticated
        if (!isAuthenticated) {
            router.push('/login')
            return
        }

        if (!hasRequiredPermissions) {
            router.push('/dashboard')
            return
        }
    }, [isAuthenticated, isLoading, hasRequiredPermissions, router])

    const isProtected = isAuthenticated && hasRequiredPermissions

    return {
        isProtected,
        isLoading,
        user,
    }
}

/**
 * Hook để kiểm tra quyền admin
 * Wrapper tiện lợi cho useProtectedRoute(['system_admin'])
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
    const { isProtected, isLoading, user } = useProtectedRoute(['system_admin'])

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
