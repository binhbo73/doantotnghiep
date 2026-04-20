/**
 * Custom Hook: useDepartmentOptions
 * Frontend standard flow for fetching department data for dropdowns
 * Follows the same pattern as useUsers
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/services/api'

export interface Department {
    id: string
    name: string
    description: string
    parent_id: string | null
    manager_id: string | null
    manager_name: string | null
    member_count: number
    created_at: string
    updated_at: string
    sub_departments: Department[]
}

interface UseDepartmentOptionsState {
    data: Department[] | null
    loading: boolean
    error: string | null
    refetch: () => Promise<void>
}

export function useDepartmentOptions(): UseDepartmentOptionsState {
    const [data, setData] = useState<Department[] | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    console.log('🎯 [useDepartmentOptions] Hook rendered/updated')

    const fetchDepartments = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)

            console.log('🔄 [useDepartmentOptions] Fetching departments...')

            // API: GET /api/v1/departments - Get all departments tree
            const url = '/departments'
            console.log(`📍 [useDepartmentOptions] URL: ${url}`)

            const response = await api.get<any>(url)

            console.log('📊 [useDepartmentOptions] Full API Response:', JSON.stringify(response, null, 2).substring(0, 1000))
            console.log('📊 [useDepartmentOptions] Response keys:', Object.keys(response || {}))
            console.log('📊 [useDepartmentOptions] Response.data type:', typeof response?.data)
            console.log('📊 [useDepartmentOptions] Response.data is Array?:', Array.isArray(response?.data))

            // Defensive parsing - handle different response formats
            let items = []

            if (Array.isArray(response?.data)) {
                items = response.data
                console.log('✅ [useDepartmentOptions] Found items in response.data (array)')
            } else if (response?.data?.items) {
                items = response.data.items
                console.log('✅ [useDepartmentOptions] Found items in response.data.items')
            } else if (response?.items) {
                items = response.items
                console.log('✅ [useDepartmentOptions] Found items in response.items')
            } else {
                console.warn('⚠️ [useDepartmentOptions] Could not find items in response')
                console.warn('⚠️ [useDepartmentOptions] Response structure:', JSON.stringify(response).substring(0, 500))
            }

            if (response.success !== false || Array.isArray(response?.data)) {
                setData(items)
                console.log(`✅ [useDepartmentOptions] Successfully fetched ${items?.length || 0} departments`)
            } else {
                setError('Failed to fetch departments')
                console.error('❌ [useDepartmentOptions] API returned success=false')
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch departments'
            console.error('❌ [useDepartmentOptions] Error fetching departments:', err)
            console.error('❌ [useDepartmentOptions] Error details:', {
                message,
                cause: err instanceof Error ? err.cause : null,
            })
            setError(message)
            setData([])
        } finally {
            setLoading(false)
            console.log('🏁 [useDepartmentOptions] Fetch completed')
        }
    }, [])

    useEffect(() => {
        console.log('🔔 [useDepartmentOptions] useEffect triggered, calling fetchDepartments')
        fetchDepartments()
    }, [fetchDepartments])

    return {
        data,
        loading,
        error,
        refetch: fetchDepartments,
    }
}
