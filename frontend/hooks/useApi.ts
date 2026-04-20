// hooks/useApi.ts - Hook for API calls with error handling
import { useState, useCallback } from 'react'
import { api, ApiError, NetworkError, TimeoutError } from '@/services/api'

interface UseApiOptions {
    onSuccess?: (data: unknown) => void
    onError?: (error: Error) => void
    timeout?: number
}

export function useApi(options?: UseApiOptions) {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<Error | null>(null)
    const [data, setData] = useState<unknown>(null)

    const request = useCallback(
        async (
            endpoint: string,
            method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' = 'GET',
            payload?: unknown
        ) => {
            setLoading(true)
            setError(null)
            try {
                let result
                if (method === 'GET') {
                    result = await api.get(endpoint, { timeout: options?.timeout })
                } else if (method === 'POST') {
                    result = await api.post(endpoint, payload, { timeout: options?.timeout })
                } else if (method === 'PUT') {
                    result = await api.put(endpoint, payload, { timeout: options?.timeout })
                } else if (method === 'PATCH') {
                    result = await api.patch(endpoint, payload, { timeout: options?.timeout })
                } else if (method === 'DELETE') {
                    result = await api.delete(endpoint, { timeout: options?.timeout })
                }

                setData(result)
                options?.onSuccess?.(result)
                return result
            } catch (err) {
                let error: Error

                if (err instanceof ApiError) {
                    error = new Error(`API Error: ${err.message}`)
                } else if (err instanceof NetworkError) {
                    error = new Error(`Network Error: ${err.message}`)
                } else if (err instanceof TimeoutError) {
                    error = new Error(err.message)
                } else {
                    error = err instanceof Error ? err : new Error(String(err))
                }

                setError(error)
                options?.onError?.(error)
                throw error
            } finally {
                setLoading(false)
            }
        },
        [options]
    )

    const reset = useCallback(() => {
        setLoading(false)
        setError(null)
        setData(null)
    }, [])

    return { request, loading, error, data, reset }
}
