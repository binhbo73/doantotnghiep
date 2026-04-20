'use client'

import { useState, useCallback } from 'react'
import { api } from '@/services/api'

interface UpdateRolePayload {
    name?: string
    description?: string
    permission_ids?: string[]
}

interface UpdateRoleResponse {
    id: string
    code: string
    name: string
    description?: string
    permission_count?: number
}

interface UseUpdateRoleReturn {
    loading: boolean
    error: Error | null
    updateRole: (roleId: string, payload: UpdateRolePayload) => Promise<UpdateRoleResponse>
    reset: () => void
}

export function useUpdateRole(): UseUpdateRoleReturn {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<Error | null>(null)

    const updateRole = useCallback(async (
        roleId: string,
        payload: UpdateRolePayload
    ): Promise<UpdateRoleResponse> => {
        try {
            setLoading(true)
            setError(null)

            const updatePayload: any = {}

            // Add only provided fields
            if (payload.name !== undefined) {
                updatePayload.name = payload.name
            }
            if (payload.description !== undefined) {
                updatePayload.description = payload.description
            }

            // First update role basic info
            const response = await api.put<any>(
                `/iam/roles/${roleId}`,
                updatePayload
            )

            // Handle response structure: { success, status_code, message, data: {...} }
            const roleData = response?.data || response

            if (!roleData || !roleData.id) {
                throw new Error('Không nhận được dữ liệu vai trò từ server')
            }

            // Then update permissions if provided
            if (payload.permission_ids && payload.permission_ids.length > 0) {
                // First remove all existing permissions
                try {
                    // Get current permissions to delete them
                    const permResponse = await api.get<any>(`/iam/roles/${roleId}/permissions`)
                    const currentPermissions = Array.isArray(permResponse) ? permResponse : (permResponse?.data || [])

                    // Delete each permission
                    for (const perm of currentPermissions) {
                        try {
                            await api.delete<any>(`/iam/roles/${roleId}/permissions/${perm.id}`)
                        } catch (e) {
                            // Continue if delete fails (might already be deleted)
                            console.warn('Warning: Failed to delete permission:', perm.id, e)
                        }
                    }
                } catch (e) {
                    // Continue if fetching current permissions fails
                    console.warn('Warning: Failed to fetch current permissions:', e)
                }

                // Then add new permissions
                for (const permissionId of payload.permission_ids) {
                    try {
                        await api.post<any>(`/iam/roles/${roleId}/permissions`, {
                            permission_id: permissionId,
                        })
                    } catch (e) {
                        console.error('Failed to add permission:', permissionId, e)
                    }
                }
            }

            return roleData as UpdateRoleResponse
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Lỗi cập nhật vai trò')
            setError(error)
            throw error
        } finally {
            setLoading(false)
        }
    }, [])

    const reset = useCallback(() => {
        setError(null)
        setLoading(false)
    }, [])

    return {
        loading,
        error,
        updateRole,
        reset,
    }
}
