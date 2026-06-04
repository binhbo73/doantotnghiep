'use client'

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/services/api'

export interface User {
    id: string
    account_id: string
    username: string
    email: string
    full_name: string
    is_active: boolean
    created_at: string
}

interface UseUserListState {
    data: User[] | null
    loading: boolean
    error: string | null
    refetch: () => Promise<void>
}

export function useUserList(pageSize: number = 100, enabled: boolean = true): UseUserListState {
    const [data, setData] = useState<User[] | null>(null)
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

            const response = await api.get<any>(`/users?page=1&page_size=${pageSize}`)

            let items = []
            if (response?.data?.items) {
                items = response.data.items
            } else if (response?.items) {
                items = response.items
            } else if (Array.isArray(response?.data)) {
                items = response.data
            }

            if (response.success !== false || Array.isArray(response?.data?.items)) {
                const mappedUsers = items
                    .filter((u: any) => u.is_active !== false && u.account_id)
                    .map((u: any) => ({
                        id: u.account_id,
                        account_id: u.account_id,
                        username: u.username,
                        email: u.email,
                        full_name: u.full_name,
                        is_active: u.is_active,
                        created_at: u.created_at,
                    }))

                setData(mappedUsers)
            } else {
                setError('Failed to fetch users')
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch users'
            setError(message)
            setData([])
        } finally {
            setLoading(false)
        }
    }, [pageSize, enabled])

    useEffect(() => {
        fetchUsers()
    }, [fetchUsers])

    return { data, loading, error, refetch: fetchUsers }
}
