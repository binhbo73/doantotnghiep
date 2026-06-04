'use client'

/**
 * Refreshes current-user roles and permissions from the backend.
 */

import { useCallback } from 'react'
import { api } from '@/services/api/client'
import { useAuthContext } from '@/context'
import { logger } from '@/services/logger'

type CurrentUserPermissions = {
    user: any
    roles: any[]
    permissions: string[]
    department_id: string | null
}

type CurrentUserResponse = CurrentUserPermissions | {
    success?: boolean
    data?: CurrentUserPermissions
}

let inFlightRefresh: Promise<CurrentUserPermissions | null> | null = null
let lastRefreshStartedAt = 0
const REFRESH_DEDUPE_WINDOW_MS = 1500

function normalizeCurrentUserResponse(response: CurrentUserResponse): CurrentUserPermissions | null {
    const payload = 'data' in response && response.data
        ? response.data
        : response as CurrentUserPermissions

    if (('success' in response && response.success === false) || !payload?.user) {
        return null
    }

    return payload
}

export function useRefreshUserPermissions() {
    const { updateUser } = useAuthContext()

    const refreshUserPermissions = useCallback(async () => {
        try {
            const now = Date.now()
            if (!inFlightRefresh || now - lastRefreshStartedAt >= REFRESH_DEDUPE_WINDOW_MS) {
                lastRefreshStartedAt = now
                inFlightRefresh = api.get<CurrentUserResponse>('/auth/me')
                    .then(normalizeCurrentUserResponse)
                    .finally(() => {
                        inFlightRefresh = null
                    })
            } else {
                logger.debug('Reusing in-flight permission refresh')
            }

            const payload = await inFlightRefresh
            if (!payload?.user) {
                logger.warn('Failed to refresh user: invalid response')
                return
            }

            const { user, roles, permissions, department_id } = payload

            localStorage.setItem('current_user', JSON.stringify(user))
            localStorage.setItem('user_roles', JSON.stringify(roles || []))
            localStorage.setItem('user_permissions', JSON.stringify(permissions || []))
            if (department_id) {
                localStorage.setItem('user_department_id', department_id)
            } else {
                localStorage.removeItem('user_department_id')
            }

            updateUser({
                id: user.id,
                email: user.email,
                name: `${user.first_name || ''} ${user.last_name || ''}`.trim(),
                username: user.username,
                roles: roles || [],
                department_id: department_id || null,
                permissions: permissions || [],
            })

            logger.info('User permissions refreshed successfully', {
                userId: user.id,
                roleCount: roles?.length || 0,
                permissionCount: permissions?.length || 0,
            })
        } catch (error) {
            logger.warn('Failed to refresh user permissions', {
                error: error instanceof Error ? error.message : String(error),
            })
        }
    }, [updateUser])

    return { refreshUserPermissions }
}
