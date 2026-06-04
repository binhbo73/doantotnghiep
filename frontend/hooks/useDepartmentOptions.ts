/**
 * Custom Hook: useDepartmentOptions
 * Fetches department data for dropdowns.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/services/api'

export interface Department {
    id: string
    name: string
    description: string
    parent_id: string | null
    manager_id: string | null
    manager_name: string | null
    member_count: number
    created_at: string
    updated_at: string
    sub_departments: Department[]
}

interface UseDepartmentOptionsState {
    data: Department[] | null
    loading: boolean
    error: string | null
    refetch: () => Promise<void>
}

export function useDepartmentOptions(enabled: boolean = true): UseDepartmentOptionsState {
    const [data, setData] = useState<Department[] | null>(null)
    const [loading, setLoading] = useState(enabled)
    const [error, setError] = useState<string | null>(null)

    const fetchDepartments = useCallback(async () => {
        if (!enabled) {
            setLoading(false)
            setError(null)
            return
        }

        try {
            setLoading(true)
            setError(null)

            const response = await api.get<any>('/departments')

            let items: Department[] = []
            if (Array.isArray(response?.data)) {
                items = response.data
            } else if (Array.isArray(response?.data?.items)) {
                items = response.data.items
            } else if (Array.isArray(response?.items)) {
                items = response.items
            } else {
                console.warn('[useDepartmentOptions] Could not find items in response')
            }

            if (response.success !== false || Array.isArray(response?.data)) {
                setData(items)
            } else {
                setError('Failed to fetch departments')
                console.error('[useDepartmentOptions] API returned success=false')
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch departments'
            console.error('[useDepartmentOptions] Error fetching departments:', err)
            setError(message)
            setData([])
        } finally {
            setLoading(false)
        }
    }, [enabled])

    useEffect(() => {
        fetchDepartments()
    }, [fetchDepartments])

    return {
        data,
        loading,
        error,
        refetch: fetchDepartments,
    }
}
