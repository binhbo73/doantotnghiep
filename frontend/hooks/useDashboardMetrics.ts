/**
 * Lightweight dashboard metrics hooks.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/services/api'

export interface Department {
    id: string
    name: string
    parent_id?: string | null
    description?: string
    manager?: any
    sub_departments?: Department[]
    is_deleted: boolean
    created_at: string
    updated_at: string
    [key: string]: any
}

interface UseDepartmentsState {
    data: Department[] | null
    count: number
    loading: boolean
    error: string | null
    refetch: () => Promise<void>
}

export function useDepartments(enabled: boolean = true): UseDepartmentsState {
    const [data, setData] = useState<Department[] | null>(null)
    const [count, setCount] = useState(0)
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

            const response = await api.get<any>('/departments/?page=1&page_size=1')
            const total = response?.data?.pagination?.total_items || response?.pagination?.total_items || 0
            const items = response?.data?.items || response?.items || []

            if (response.success !== false) {
                setCount(total)
                setData(items)
            } else {
                setError('Failed to fetch departments')
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch departments'
            setError(message)
            console.error('Error fetching departments:', err)
        } finally {
            setLoading(false)
        }
    }, [enabled])

    useEffect(() => {
        fetchDepartments()
    }, [fetchDepartments])

    return {
        data,
        count,
        loading,
        error,
        refetch: fetchDepartments,
    }
}
