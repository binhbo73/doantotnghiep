/**
 * Custom Hook: useDepartments
 * Frontend standard flow for fetching department data
 * 
 * Usage:
 * const { data, count, loading, error } = useDepartments()
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

export interface PaginatedResponse<T> {
    success: boolean
    data: {
        items: T[]
        pagination: {
            page: number
            page_size: number
            total_items: number
            total_pages: number
            has_next?: boolean
            has_previous?: boolean
        }
    }
    message: string
    timestamp: string
    request_id: string
}

interface UseDepartmentsState {
    data: Department[] | null
    count: number
    loading: boolean
    error: string | null
    refetch: () => Promise<void>
}

export function useDepartments(): UseDepartmentsState {
    const [data, setData] = useState<Department[] | null>(null)
    const [count, setCount] = useState(0)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchDepartments = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)

            // API: GET /api/v1/departments?page=1&page_size=1 (chỉ lấy count)
            const response = await api.get<any>('/departments/?page=1&page_size=1')

            console.log('📊 Departments API Response:', JSON.stringify(response, null, 2).substring(0, 500))

            // Defensive parsing - handle different response formats
            const total = response?.data?.pagination?.total_items || response?.pagination?.total_items || 0
            const items = response?.data?.items || response?.items || []

            if (response.success !== false) {
                setCount(total)
                setData(items)
                console.log(`✅ Fetched departments successfully - count: ${total}`)
            } else {
                setError('Failed to fetch departments')
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch departments'
            setError(message)
            console.error('❌ Error fetching departments:', err)
        } finally {
            setLoading(false)
        }
    }, [])

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
