'use client'

/**
 * Custom Hook: useRoleOptions
 * Fetches role data with pagination for dropdowns.
 */



import { useState, useEffect, useCallback } from 'react'
import { api } from '@/services/api'

export interface Role {
    id: string
    code: string
    name: string
    description: string
    is_custom: boolean
    permission_count: number
    created_at: string
    updated_at: string
}

interface UseRoleOptionsState {
    data: Role[] | null
    loading: boolean
    error: string | null
    refetch: () => Promise<void>
}

export function useRoleOptions(pageSize: number = 100, enabled: boolean = true): UseRoleOptionsState {
    const [data, setData] = useState<Role[] | null>(null)
    const [loading, setLoading] = useState(enabled)
    const [error, setError] = useState<string | null>(null)

    const fetchRoles = useCallback(async () => {
        if (!enabled) {
            setLoading(false)
            setError(null)
            return
        }

        try {
            setLoading(true)
            setError(null)

            const response = await api.get<any>(`/iam/roles?page=1&page_size=${pageSize}`)

            let items: Role[] = []
            if (Array.isArray(response?.data?.items)) {
                items = response.data.items
            } else if (Array.isArray(response?.items)) {
                items = response.items
            } else if (Array.isArray(response?.data)) {
                items = response.data
            } else {
                console.warn('[useRoleOptions] Could not find items in response')
            }

            if (response.success !== false || Array.isArray(response?.data?.items)) {
                setData(items)
            } else {
                setError('Failed to fetch roles')
                console.error('[useRoleOptions] API returned success=false')
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch roles'
            console.error('[useRoleOptions] Error fetching roles:', err)
            setError(message)
            setData([])
        } finally {
            setLoading(false)
        }
    }, [pageSize, enabled])

    useEffect(() => {
        fetchRoles()
    }, [fetchRoles])

    return {
        data,
        loading,
        error,
        refetch: fetchRoles,
    }
}
