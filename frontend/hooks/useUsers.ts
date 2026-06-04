/**
 * Custom Hook: useUsers
 * Fetches user count/list for lightweight dashboard widgets.
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

interface UseUsersState {
    data: User[] | null
    count: number
    loading: boolean
    error: string | null
    refetch: () => Promise<void>
}

export function useUsers(enabled: boolean = true): UseUsersState {
    const [data, setData] = useState<User[] | null>(null)
    const [count, setCount] = useState(0)
    const [loading, setLoading] = useState(enabled)
    const [error, setError] = useState<string | null>(null)

    const fetchUsers = useCallback(async () => {
        if (!enabled) {
            setLoading(false)
            setError(null)
            return
        }

        try {
            setLoading(true)
            setError(null)

            const response = await api.get<any>('/users/?page=1&page_size=1')
            const total = response?.data?.pagination?.total_items || response?.pagination?.total_items || 0
            const items = response?.data?.items || response?.items || []

            if (response.success !== false) {
                setCount(total)
                setData(items)
            } else {
                setError('Failed to fetch users')
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch users'
            setError(message)
            console.error('Error fetching users:', err)
        } finally {
            setLoading(false)
        }
    }, [enabled])

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
