'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchRoles, RolesQueryParams } from '@/services/iam'
import { IamRole, PaginationInfo } from '@/types/api'

const EMPTY_ROLES: IamRole[] = []

const FALLBACK_PAGINATION: PaginationInfo = {
    page: 1,
    page_size: 100,
    total_items: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false,
}

export function useRoles(initialParams?: RolesQueryParams, enabled: boolean = true) {
    const [roles, setRoles] = useState<IamRole[]>([])
    const [loading, setLoading] = useState(enabled)
    const [error, setError] = useState<Error | null>(null)
    const [pagination, setPagination] = useState<PaginationInfo | null>(null)
    const [useFallback, setUseFallback] = useState(false)
    const hasLoadedRef = useRef(false)

    const loadRoles = useCallback(async (params?: RolesQueryParams) => {
        if (!enabled) {
            setLoading(false)
            setError(null)
            return
        }

        setLoading(true)
        setError(null)
        setUseFallback(false)
        try {
            const response = await fetchRoles(params || initialParams)
            const responseData = response.data as any
            const loadedRoles = Array.isArray(responseData)
                ? responseData
                : responseData?.items || []
            const loadedPagination = responseData?.pagination || response.pagination

            setRoles(loadedRoles)
            setPagination(loadedPagination)
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Failed to fetch roles')
            setError(error)
            console.error('Error loading roles:', error)
            setRoles(EMPTY_ROLES)
            setPagination(FALLBACK_PAGINATION)
            setUseFallback(false)
        } finally {
            setLoading(false)
        }
    }, [initialParams, enabled])

    useEffect(() => {
        if (!enabled || hasLoadedRef.current) return
        hasLoadedRef.current = true
        loadRoles()
    }, [enabled, loadRoles])

    return {
        roles,
        loading,
        error,
        pagination,
        useFallback,
        refetch: loadRoles,
    }
}
