'use client'

import { useState, useCallback } from 'react'
import { api } from '@/services/api'

interface UseDeleteRoleReturn {
    loading: boolean
    error: Error | null
    deleteRole: (roleId: string) => Promise<void>
    reset: () => void
}

export function useDeleteRole(): UseDeleteRoleReturn {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<Error | null>(null)

    const deleteRole = useCallback(async (roleId: string): Promise<void> => {
        try {
            setLoading(true)
            setError(null)

            await api.delete(`/iam/roles/${roleId}`)
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Lỗi xóa vai trò')
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
        deleteRole,
        reset,
    }
}
