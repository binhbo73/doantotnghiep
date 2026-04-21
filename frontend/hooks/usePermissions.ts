'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchPermissions, PermissionsQueryParams } from '@/services/iam'
import { IamPermission, ApiResponseWithPagination, PaginationInfo } from '@/types/api'

// Fallback demo data for testing UI
const FALLBACK_PERMISSIONS: IamPermission[] = [
    {
        id: 'd322d471-24b5-47ee-b1cf-d99caf5ab1ba',
        code: 'user_create',
        resource: 'users',
        action: 'create',
        description: 'Create new user account',
        created_at: '2026-04-07T16:20:57.105978Z',
    },
    {
        id: '3f5dbda2-02dd-4ce8-adbb-c309902d1a3a',
        code: 'user_change_role',
        resource: 'users',
        action: 'change_role',
        description: 'Assign/remove roles from user',
        created_at: '2026-04-07T16:20:57.119946Z',
    },
    {
        id: '46822ff4-709b-4520-bb9b-bb82a4cc4740',
        code: 'document_create',
        resource: 'documents',
        action: 'create',
        description: 'Upload/create documents',
        created_at: '2026-04-07T16:20:57.129348Z',
    },
    {
        id: '66c43f3c-c820-46cb-93a7-6a5ed9b031a8',
        code: 'document_delete',
        resource: 'documents',
        action: 'delete',
        description: 'Delete documents',
        created_at: '2026-04-07T16:20:57.147002Z',
    },
    {
        id: 'dc213be9-7310-4244-ad10-de45a61d7034',
        code: 'chat_create',
        resource: 'chat',
        action: 'create',
        description: 'Start chat conversation',
        created_at: '2026-04-07T16:20:57.201683Z',
    },
]

const FALLBACK_PAGINATION: PaginationInfo = {
    page: 1,
    page_size: 20,
    total_items: 22,
    total_pages: 2,
    has_next: true,
    has_prev: false,
}

export function usePermissions(initialParams?: PermissionsQueryParams) {
    const [permissions, setPermissions] = useState<IamPermission[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<Error | null>(null)
    const [pagination, setPagination] = useState<PaginationInfo | null>(null)
    const [useFallback, setUseFallback] = useState(false)

    // Use ref to track if we've already loaded
    const hasLoadedRef = useRef(false)

    const loadPermissions = useCallback(async (params?: PermissionsQueryParams) => {
        setLoading(true)
        setError(null)
        setUseFallback(false)
        try {
            const response = await fetchPermissions(params || initialParams)
            // Extract data and pagination from response
            // Backend returns { data: { items: [...], pagination: {...} } }
            const responseData = response.data as any
            const permissions = Array.isArray(responseData)
                ? responseData
                : responseData?.items || []
            const pagination = responseData?.pagination || response.pagination

            setPermissions(permissions)
            setPagination(pagination)
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Failed to fetch permissions')
            setError(error)
            console.error('Error loading permissions, using fallback data:', error)
            // Use fallback data for testing
            setPermissions(FALLBACK_PERMISSIONS)
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
            loadPermissions()
        }
    }, []) // Empty dependency array - load only once

    return {
        permissions,
        loading,
        error,
        pagination,
        useFallback,
        refetch: loadPermissions,
    }
}
