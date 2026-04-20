/**
 * Custom Hook: useUsers
 * Frontend standard flow for fetching user data
 * 
 * Usage:
 * const { data, count, loading, error } = useUsers()
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/services/api'

export interface User {
    id: string
    username: string
    email: string
    first_name: string
    last_name: string
    status: 'active' | 'blocked' | 'inactive'
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

interface UseUsersState {
    data: User[] | null
    count: number
    loading: boolean
    error: string | null
    refetch: () => Promise<void>
}

export function useUsers(): UseUsersState {
    const [data, setData] = useState<User[] | null>(null)
    const [count, setCount] = useState(0)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchUsers = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)

            // API: GET /api/v1/users?page=1&page_size=1 (chỉ lấy count)
            const response = await api.get<any>('/users/?page=1&page_size=1')

            console.log('📊 Users API Response:', JSON.stringify(response, null, 2).substring(0, 500))

            // Defensive parsing - handle different response formats
            const total = response?.data?.pagination?.total_items || response?.pagination?.total_items || 0
            const items = response?.data?.items || response?.items || []

            if (response.success !== false) {
                setCount(total)
                setData(items)
                console.log(`✅ Fetched users successfully - count: ${total}`)
            } else {
                setError('Failed to fetch users')
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch users'
            setError(message)
            console.error('❌ Error fetching users:', err)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchUsers()
    }, [fetchUsers])

    return {
        data,
        count,
        loading,
        error,
        refetch: fetchUsers,
    }
}
