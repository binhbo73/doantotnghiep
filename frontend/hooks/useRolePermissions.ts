'use client'

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/services/api'
import { IamPermission, ApiResponseWithPagination } from '@/types/api'

interface UseRolePermissionsReturn {
    permissions: IamPermission[]
    loading: boolean
    error: Error | null
    refetch: () => Promise<void>
}

export function useRolePermissions(roleId: string): UseRolePermissionsReturn {
    const [permissions, setPermissions] = useState<IamPermission[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<Error | null>(null)

    const fetchPermissions = useCallback(async () => {
        if (!roleId) {
            setPermissions([])
            setLoading(false)
            return
        }

        try {
            setLoading(true)
            setError(null)

            const response = await api.get<ApiResponseWithPagination<IamPermission>>(
                `/iam/roles/${roleId}/permissions?page=1&page_size=100`
            )

            if (!response.success) {
                throw new Error(response.message || 'Failed to fetch role permissions')
            }

            // Backend returns { data: { items: [...], pagination: {...} } }
            const responseData = response.data as any
            const permissions = Array.isArray(responseData)
                ? responseData
                : responseData?.items || []
            setPermissions(permissions)
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Failed to fetch role permissions')
            setError(error)
            console.error('Error fetching role permissions:', err)
            setPermissions([])
        } finally {
            setLoading(false)
        }
    }, [roleId])

    useEffect(() => {
        fetchPermissions()
    }, [fetchPermissions])

    const refetch = useCallback(async () => {
        await fetchPermissions()
    }, [fetchPermissions])

    return {
        permissions,
        loading,
        error,
        refetch,
    }
}
