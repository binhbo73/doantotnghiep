'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchDepartments, createDepartment, updateDepartment, deleteDepartment, DepartmentQueryParams } from '@/services/department'
import { Department, PaginationInfo } from '@/types/api'

export function useDepartments(initialParams?: DepartmentQueryParams) {
    const [departments, setDepartments] = useState<Department[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<Error | null>(null)
    const [pagination, setPagination] = useState<PaginationInfo | null>(null)
    const [searchQuery, setSearchQuery] = useState('')

    const hasLoadedRef = useRef(false)

    const loadDepartments = useCallback(async (params?: DepartmentQueryParams) => {
        setIsLoading(true)
        setError(null)
        try {
            const response = await fetchDepartments(params || {})
            const responseData = response.data as unknown
            const departments = Array.isArray(responseData)
                ? responseData
                : Array.isArray((responseData as { items?: Department[] } | null | undefined)?.items)
                    ? (responseData as { items: Department[] }).items
                    : []
            const pagination = (responseData as { pagination?: PaginationInfo } | null | undefined)?.pagination || response.pagination || null

            setDepartments(departments)
            setPagination(pagination)
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Failed to fetch departments')
            setError(error)
            console.error('Error loading departments:', error)
            setDepartments([])
            setPagination(null)
        } finally {
            setIsLoading(false)
        }
    }, [])

    // Load departments only once on mount
    useEffect(() => {
        if (!hasLoadedRef.current) {
            hasLoadedRef.current = true
            loadDepartments()
        }
    }, [loadDepartments]) // loadDepartments won't change because no dependencies

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
        searchQuery,
        setSearchQuery,
        addDepartment,
        updateDepartment: editDepartment,
        deleteDepartment: removeDepartment,
        refetch: loadDepartments,
        getStats,
    }
}
