'use client'

/**
 * useRefreshUserPermissions Hook
 * Refreshes current user's data from backend (roles, permissions, etc)
 * Called after any permission/role changes to update UI immediately
 */

import { useCallback } from 'react'
import { api } from '@/services/api/client'
import { setAuthData } from '@/services/auth'
import { useAuthContext } from '@/context'
import { logger } from '@/services/logger'
import type { LoginData } from '@/types/api'

export function useRefreshUserPermissions() {
    const { updateUser } = useAuthContext()

    const refreshUserPermissions = useCallback(async () => {
        try {
            logger.info('🔄 Refreshing user permissions from backend...')

            // Fetch current user data from backend
            const response = await api.get<{ user: any; roles: any[]; permissions: string[]; department_id: string }>('/auth/me')

            if (!response.success || !response.data) {
                logger.warn('⚠️ Failed to refresh user: Invalid response')
                return
            }

            // Extract user data from response
            const { user, roles, permissions, department_id } = response.data

            // Update localStorage + cookies via setAuthData
            const loginData: LoginData = {
                access_token: '', // Don't update token on permission refresh
                user,
                roles: roles || [],
                permissions: permissions || [],
                department_id: department_id || '',
            }

            // Update localStorage (but don't override tokens)
            if (user) {
                localStorage.setItem('current_user', JSON.stringify(user))
            }
            if (roles && roles.length > 0) {
                localStorage.setItem('user_roles', JSON.stringify(roles))
            }
            if (permissions && permissions.length > 0) {
                localStorage.setItem('user_permissions', JSON.stringify(permissions))
            }
            if (department_id) {
                localStorage.setItem('user_department_id', department_id)
            }

            // Update AuthContext state
            if (user && roles) {
                updateUser({
                    id: user.id,
                    email: user.email,
                    name: `${user.first_name || ''} ${user.last_name || ''}`.trim(),
                    username: user.username,
                    roles: roles,
                    department_id: department_id || null,
                    permissions: permissions || [],
                })

                logger.info('✅ User permissions refreshed successfully', {
                    userId: user.id,
                    roleCount: roles.length,
                    permissionCount: permissions.length,
                })
            }
        } catch (error) {
            logger.error('❌ Failed to refresh user permissions', {
                error: error instanceof Error ? error.message : String(error),
            })
            // Don't throw - let components handle gracefully
        }
    }, [updateUser])

    return { refreshUserPermissions }
}
