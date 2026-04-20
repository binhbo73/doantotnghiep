/**
 * Custom Hook: useDocuments
 * Frontend standard flow for fetching document data
 * 
 * Usage:
 * const { data, count, loading, error } = useDocuments()
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/services/api'

export interface Document {
    id: string
    original_name: string
    file_type: string
    file_size: number
    status: 'pending' | 'processing' | 'completed' | 'failed'
    uploader_id: string
    folder_id?: string
    created_at: string
    updated_at: string
    [key: string]: any
}

export interface PaginatedResponse<T> {
    success: boolean
    data: {
        items: T[]
        pagination: {
            page: number
            page_size: number
            total_items: number
            total_pages: number
            has_next?: boolean
            has_previous?: boolean
        }
    }
    message: string
    timestamp: string
    request_id: string
}

interface UseDocumentsState {
    data: Document[] | null
    count: number
    loading: boolean
    error: string | null
    refetch: () => Promise<void>
}

export function useDocuments(): UseDocumentsState {
    const [data, setData] = useState<Document[] | null>(null)
    const [count, setCount] = useState(0)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchDocuments = useCallback(async () => {
        try {
            setLoading(true)
            setError(null)

            // API: GET /api/v1/documents?page=1&page_size=1 (chỉ lấy count)
            const response = await api.get<any>('/documents/?page=1&page_size=1')

            console.log('📊 Documents API Response:', JSON.stringify(response, null, 2).substring(0, 500))

            // Defensive parsing - handle different response formats
            const total = response?.data?.pagination?.total_items || response?.pagination?.total_items || 0
            const items = response?.data?.items || response?.items || []

            if (response.success !== false) {
                setCount(total)
                setData(items)
                console.log(`✅ Fetched documents successfully - count: ${total}`)
            } else {
                setError('Failed to fetch documents')
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch documents'
            setError(message)
            console.error('❌ Error fetching documents:', err)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchDocuments()
    }, [fetchDocuments])

    return {
        data,
        count,
        loading,
        error,
        refetch: fetchDocuments,
    }
}
