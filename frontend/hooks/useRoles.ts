'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchRoles, RolesQueryParams } from '@/services/iam'
import { IamRole, ApiResponseWithPagination, PaginationInfo } from '@/types/api'

// Fallback demo data for testing UI
const FALLBACK_ROLES: IamRole[] = [
    {
        id: '009bd00e-3fef-4edf-8e81-9507b9378b6c',
        code: 'admin',
        name: 'Administrator',
        description: 'Full system access - manage everything',
        created_at: '2026-04-07T16:20:57.216237Z',
        updated_at: '2026-04-07T16:20:57.216248Z',
        permission_count: 23,
    },
    {
        id: '243d9952-4c18-45cc-bc33-9d5efe312ff7',
        code: 'manager',
        name: 'Manager',
        description: 'Department manager - manage documents and team members',
        created_at: '2026-04-07T16:20:57.305416Z',
        updated_at: '2026-04-07T16:20:57.305425Z',
        permission_count: 15,
    },
    {
        id: 'a2584097-84ec-441b-9c24-2efc52c7d445',
        code: 'user',
        name: 'User',
        description: 'Regular user - basic document and query access',
        created_at: '2026-04-07T16:20:57.366234Z',
        updated_at: '2026-04-07T16:20:57.366247Z',
        permission_count: 6,
    },
]

const FALLBACK_PAGINATION: PaginationInfo = {
    page: 1,
    page_size: 100,
    total_items: 3,
    total_pages: 1,
    has_next: false,
    has_prev: false,
}

export function useRoles(initialParams?: RolesQueryParams) {
    const [roles, setRoles] = useState<IamRole[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<Error | null>(null)
    const [pagination, setPagination] = useState<PaginationInfo | null>(null)
    const [useFallback, setUseFallback] = useState(false)
    
    // Use ref to track if we've already loaded
    const hasLoadedRef = useRef(false)

    const loadRoles = useCallback(async (params?: RolesQueryParams) => {
        setLoading(true)
        setError(null)
        setUseFallback(false)
        try {
            const response = await fetchRoles(params || initialParams)
            // Extract data and pagination from response
            setRoles(response.data)
            setPagination(response.pagination)
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Failed to fetch roles')
            setError(error)
            console.error('Error loading roles, using fallback data:', error)
            // Use fallback data for testing
            setRoles(FALLBACK_ROLES)
            setPagination(FALLBACK_PAGINATION)
            setUseFallback(true)
        } finally {
            setLoading(false)
        }
    }, [initialParams])

    useEffect(() => {
        // Only load once
        if (!hasLoadedRef.current) {
            hasLoadedRef.current = true
            loadRoles()
        }
    }, []) // Empty dependency array - load only once

    return {
        roles,
        loading,
        error,
        pagination,
        useFallback,
        refetch: loadRoles,
    }
}
