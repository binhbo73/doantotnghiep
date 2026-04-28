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
            if ('permission_ids' in payload) {
                updatePayload.permission_ids = Array.from(new Set(payload.permission_ids ?? []))
            }

            const response = await api.put<any>(
                `/iam/roles/${roleId}`,
                updatePayload
            )

            // Handle response structure: { success, status_code, message, data: {...} }
            const roleData = response?.data || response

            if (!roleData || !roleData.id) {
                throw new Error('Không nhận được dữ liệu vai trò từ server')
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
