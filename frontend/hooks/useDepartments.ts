'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchDepartments, createDepartment, updateDepartment, deleteDepartment, DepartmentQueryParams } from '@/services/department'
import { Department, ApiResponseWithPagination, PaginationInfo } from '@/types/api'

const FALLBACK_DEPARTMENTS: Department[] = [
    {
        id: 'b177325c-347c-4fb0-afb3-f258e8a0b2d5',
        name: 'Công ty mẹ',
        description: 'Parent organization',
        parent_id: null,
        manager_id: null,
        member_count: 7,
        sub_department_count: 3,
        created_at: '2026-04-07T16:20:57Z',
        updated_at: '2026-04-07T16:20:57Z'
    },
    {
        id: '2f6b655f-6a49-4093-afa3-628efeaeae3c',
        name: 'DevOps',
        description: 'DevOps and Infrastructure',
        parent_id: null,
        manager_id: '94d447d8-a1c8-4862-861c-e834f8dc88cd',
        member_count: 2,
        sub_department_count: 0,
        manager: {
            id: '94d447d8-a1c8-4862-861c-e834f8dc88cd',
            username: 'manager2',
            email: 'tien3@example.com',
            full_name: 'Huynh COng Trieu2 TIen'
        },
        created_at: '2026-04-14T07:41:37Z',
        updated_at: '2026-04-14T07:41:37Z'
    }
]

const FALLBACK_PAGINATION: PaginationInfo = {
    page: 1,
    page_size: 20,
    total_items: 2,
    total_pages: 1,
    has_next: false,
    has_prev: false
}

export function useDepartments(initialParams?: DepartmentQueryParams) {
    const [departments, setDepartments] = useState<Department[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<Error | null>(null)
    const [pagination, setPagination] = useState<PaginationInfo | null>(null)
    const [useFallback, setUseFallback] = useState(false)
    const [searchQuery, setSearchQuery] = useState('')
    
    const hasLoadedRef = useRef(false)

    const loadDepartments = useCallback(async (params?: DepartmentQueryParams) => {
        setIsLoading(true)
        setError(null)
        try {
            const response = await fetchDepartments(params || { search: searchQuery })
            setDepartments(response.data)
            setPagination(response.pagination)
            setUseFallback(false)
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Failed to fetch departments')
            setError(error)
            console.error('Error loading departments, using fallback data:', error)
            setDepartments(FALLBACK_DEPARTMENTS)
            setPagination(FALLBACK_PAGINATION)
            setUseFallback(true)
        } finally {
            setIsLoading(false)
        }
    }, [searchQuery])

    useEffect(() => {
        if (!hasLoadedRef.current) {
            hasLoadedRef.current = true
            loadDepartments()
        }
    }, [loadDepartments])

    const addDepartment = useCallback(async (data: {
        name: string
        description?: string
        parent_id?: string | null
        manager_id?: string | null
    }) => {
        try {
            await createDepartment(data)
            loadDepartments()
        } catch (err) {
            console.error('Error adding department:', err)
            throw err
        }
    }, [loadDepartments])

    const editDepartment = useCallback(async (id: string, data: Partial<{
        name: string
        description: string
        parent_id: string | null
        manager_id: string | null
    }>) => {
        try {
            await updateDepartment(id, data)
            loadDepartments()
        } catch (err) {
            console.error('Error updating department:', err)
            throw err
        }
    }, [loadDepartments])

    const removeDepartment = useCallback(async (id: string) => {
        try {
            await deleteDepartment(id)
            loadDepartments()
        } catch (err) {
            console.error('Error deleting department:', err)
            throw err
        }
    }, [loadDepartments])

    const getStats = useCallback(() => {
        return {
            totalDepartments: pagination?.total_items || departments.length,
            totalMembers: departments.reduce((sum, dept) => sum + (dept.member_count || 0), 0),
            activeDepartments: departments.length,
        }
    }, [departments, pagination])

    return {
        departments,
        isLoading,
        error,
        pagination,
        useFallback,
        searchQuery,
        setSearchQuery,
        addDepartment,
        updateDepartment: editDepartment,
        deleteDepartment: removeDepartment,
        refetch: loadDepartments,
        getStats,
    }
}
