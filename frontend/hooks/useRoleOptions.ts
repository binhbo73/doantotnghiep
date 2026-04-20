/**
 * Custom Hook: useRoleOptions
 * Frontend standard flow for fetching role data with pagination for dropdowns
 * Follows the same pattern as useUsers
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/services/api'

export interface Role {
    id: string
    code: string
    name: string
    description: string
    is_custom: boolean
    permission_count: number
    created_at: string
    updated_at: string
}

interface UseRoleOptionsState {
    data: Role[] | null
    loading: boolean
    error: string | null
    refetch: () => Promise<void>
}

export function useRoleOptions(pageSize: number = 100): UseRoleOptionsState {
    const [data, setData] = useState<Role[] | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    console.log('🎯 [useRoleOptions] Hook rendered/updated with pageSize:', pageSize)

    const fetchRoles = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)

            console.log(`🔄 [useRoleOptions] Fetching roles with pageSize=${pageSize}...`)

            // API: GET /api/v1/iam/roles?page=1&page_size=100
            const url = `/iam/roles?page=1&page_size=${pageSize}`
            console.log(`📍 [useRoleOptions] URL: ${url}`)

            const response = await api.get<any>(url)

            console.log('📊 [useRoleOptions] Full API Response:', JSON.stringify(response, null, 2).substring(0, 1000))
            console.log('📊 [useRoleOptions] Response keys:', Object.keys(response || {}))
            console.log('📊 [useRoleOptions] Response.data:', response?.data)
            console.log('📊 [useRoleOptions] Response.data.items:', response?.data?.items)
            console.log('📊 [useRoleOptions] Response.data.items length:', response?.data?.items?.length)

            // Defensive parsing - handle different response formats
            let items = []

            // Try multiple paths
            if (response?.data?.items) {
                items = response.data.items
                console.log('✅ [useRoleOptions] Found items in response.data.items')
            } else if (response?.items) {
                items = response.items
                console.log('✅ [useRoleOptions] Found items in response.items')
            } else if (Array.isArray(response?.data)) {
                items = response.data
                console.log('✅ [useRoleOptions] Response.data is array directly')
            } else {
                console.warn('⚠️ [useRoleOptions] Could not find items in response')
                console.warn('⚠️ [useRoleOptions] Response structure:', JSON.stringify(response).substring(0, 500))
            }

            if (response.success !== false || Array.isArray(response?.data?.items)) {
                setData(items)
                console.log(`✅ [useRoleOptions] Successfully fetched ${items?.length || 0} roles`)
            } else {
                setError('Failed to fetch roles')
                console.error('❌ [useRoleOptions] API returned success=false')
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch roles'
            console.error('❌ [useRoleOptions] Error fetching roles:', err)
            console.error('❌ [useRoleOptions] Error details:', {
                message,
                cause: err instanceof Error ? err.cause : null,
            })
            setError(message)
            setData([])
        } finally {
            setLoading(false)
            console.log('🏁 [useRoleOptions] Fetch completed')
        }
    }, [pageSize])

    useEffect(() => {
        console.log('🔔 [useRoleOptions] useEffect triggered, calling fetchRoles')
        fetchRoles()
    }, [fetchRoles])

    return {
        data,
        loading,
        error,
        refetch: fetchRoles,
    }
}
