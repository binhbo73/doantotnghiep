'use client'

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/services/api'

export interface User {
    id: string              // This is account_id (Account.id)
    account_id: string      // For clarity
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

export function useUserList(pageSize: number = 100): UseUserListState {
    const [data, setData] = useState<User[] | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchUsers = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)

            // API: GET /api/v1/users?page=1&page_size=100
            const url = `/users?page=1&page_size=${pageSize}`

            const response = await api.get<any>(url)

            // Defensive parsing - handle different response formats
            let items = []

            if (response?.data?.items) {
                items = response.data.items
            } else if (response?.items) {
                items = response.items
            } else if (Array.isArray(response?.data)) {
                items = response.data
            }

            if (response.success !== false || Array.isArray(response?.data?.items)) {
                // Map UserProfile to User format
                // IMPORTANT: Use account_id for manager_id, not UserProfile.id
                const mappedUsers = items
                    .filter((u: any) => u.is_active !== false && u.account_id)
                    .map((u: any) => ({
                        id: u.account_id,         // Use account_id as id for backend compatibility
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
    }, [pageSize])

    useEffect(() => {
        fetchUsers()
    }, [fetchUsers])

    return { data, loading, error, refetch: fetchUsers }
}
