'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchPermissions, PermissionsQueryParams } from '@/services/iam'
import { IamPermission, PaginationInfo } from '@/types/api'

const FALLBACK_PAGINATION: PaginationInfo = {
    page: 1,
    page_size: 20,
    total_items: 0,
    total_pages: 0,
    has_next: false,
    has_prev: false,
}

export function usePermissions(initialParams?: PermissionsQueryParams, enabled: boolean = true) {
    const [permissions, setPermissions] = useState<IamPermission[]>([])
    const [loading, setLoading] = useState(enabled)
    const [error, setError] = useState<Error | null>(null)
    const [pagination, setPagination] = useState<PaginationInfo | null>(null)
    const [useFallback, setUseFallback] = useState(false)
    const hasLoadedRef = useRef(false)

    const loadPermissions = useCallback(async (params?: PermissionsQueryParams) => {
        if (!enabled) {
            setLoading(false)
            setError(null)
            return
        }

        setLoading(true)
        setError(null)
        setUseFallback(false)
        try {
            const response = await fetchPermissions(params || initialParams)
            const responseData = response.data as any
            const loadedPermissions = Array.isArray(responseData)
                ? responseData
                : responseData?.items || []
            const loadedPagination = responseData?.pagination || response.pagination

            setPermissions(loadedPermissions)
            setPagination(loadedPagination)
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Failed to fetch permissions')
            setError(error)
            console.error('Error loading permissions:', error)
            setPermissions([])
            setPagination(FALLBACK_PAGINATION)
            setUseFallback(false)
        } finally {
            setLoading(false)
        }
    }, [initialParams, enabled])

    useEffect(() => {
        if (!enabled || hasLoadedRef.current) return
        hasLoadedRef.current = true
        loadPermissions()
    }, [enabled, loadPermissions])

    return {
        permissions,
        loading,
        error,
        pagination,
        useFallback,
        refetch: loadPermissions,
    }
}
