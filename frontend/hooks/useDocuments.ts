'use client'

/**
 * Custom Hook: useDocuments
 * Fetches document count/list for lightweight dashboard widgets.
 */



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

interface UseDocumentsState {
    data: Document[] | null
    count: number
    loading: boolean
    error: string | null
    refetch: () => Promise<void>
}

export function useDocuments(enabled: boolean = true): UseDocumentsState {
    const [data, setData] = useState<Document[] | null>(null)
    const [count, setCount] = useState(0)
    const [loading, setLoading] = useState(enabled)
    const [error, setError] = useState<string | null>(null)

    const fetchDocuments = useCallback(async () => {
        if (!enabled) {
            setLoading(false)
            setError(null)
            return
        }

        try {
            setLoading(true)
            setError(null)

            const response = await api.get<any>('/documents/?page=1&page_size=1')
            const total = response?.data?.pagination?.total_items || response?.pagination?.total_items || 0
            const items = response?.data?.items || response?.items || []

            if (response.success !== false) {
                setCount(total)
                setData(items)
            } else {
                setError('Failed to fetch documents')
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch documents'
            setError(message)
            console.error('Error fetching documents:', err)
        } finally {
            setLoading(false)
        }
    }, [enabled])

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
