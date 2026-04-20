'use client'

import { useState, useCallback } from 'react'
import { api } from '@/services/api'

interface CreateRolePayload {
    code: string
    name: string
    description?: string
}

interface RolePermissionPayload {
    permission_ids: string[]
}

interface CreateRoleResponse {
    id: string
    code: string
    name: string
    description?: string
}

interface UseCreateRoleReturn {
    loading: boolean
    error: Error | null
    createRole: (payload: CreateRolePayload) => Promise<CreateRoleResponse>
    addPermissionsToRole: (roleId: string, payload: RolePermissionPayload) => Promise<void>
    reset: () => void
}

export function useCreateRole(): UseCreateRoleReturn {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<Error | null>(null)

    const createRole = useCallback(async (payload: CreateRolePayload): Promise<CreateRoleResponse> => {
        try {
            setLoading(true)
            setError(null)

            const response = await api.post<any>(
                '/iam/roles',
                {
                    code: payload.code,
                    name: payload.name,
                    description: payload.description || '',
                }
            )

            // Handle the response structure - the api returns { data, success, message }
            const roleData = response.data || response

            if (!roleData || !roleData.id) {
                throw new Error('Không nhận được dữ liệu vai trò từ server')
            }

            return roleData as CreateRoleResponse
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Lỗi tạo vai trò')
            setError(error)
            throw error
        } finally {
            setLoading(false)
        }
    }, [])

    const addPermissionsToRole = useCallback(
        async (roleId: string, payload: RolePermissionPayload): Promise<void> => {
            try {
                setLoading(true)
                setError(null)

                // Add each permission individually since backend expects one at a time
                for (const permissionId of payload.permission_ids) {
                    await api.post(`/iam/roles/${roleId}/permissions`, {
                        permission_id: permissionId,
                    })
                }
            } catch (err) {
                const error = err instanceof Error ? err : new Error('Lỗi thêm quyền hạn vào vai trò')
                setError(error)
                throw error
            } finally {
                setLoading(false)
            }
        },
        []
    )

    const reset = useCallback(() => {
        setError(null)
        setLoading(false)
    }, [])

    return {
        loading,
        error,
        createRole,
        addPermissionsToRole,
        reset,
    }
}
