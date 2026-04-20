/**
 * API Client - Main HTTP client with middleware, retry logic, and error handling
 */

import { requestMiddleware } from './middleware/request'
import { responseMiddleware } from './middleware/response'
import { errorMiddleware } from './middleware/error'
import { ApiError, NetworkError, TimeoutError } from './errors'
import { logger } from '@/services/logger'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface RequestOptions extends Omit<RequestInit, 'body'> {
    timeout?: number
    retries?: number
    tags?: string[]
    onProgress?: (progress: number) => void
}

interface RequestConfig {
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'HEAD'
    endpoint: string
    data?: unknown
    options?: RequestOptions
}

class ApiClient {
    private baseUrl: string

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl
    }

    /**
     * Main request method
     */
    async request<T>(
        method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'HEAD',
        endpoint: string,
        data?: unknown,
        options?: RequestOptions
    ): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`

        // Create initial request to apply middleware
        let request = new Request(url, {
            method,
            headers: {},
        })

        // Apply request middleware to get headers and body
        const enrichedRequest = await requestMiddleware(request, data)
        const requestId = enrichedRequest.__metadata?.requestId

        // Extract metadata and prepare for retry
        const headers = Object.fromEntries(enrichedRequest.headers.entries())
        let body: BodyInit | undefined

        // Get body only once (avoid consuming stream twice)
        if (enrichedRequest.method !== 'GET' && enrichedRequest.method !== 'HEAD') {
            const bodyText = await enrichedRequest.text()
            if (bodyText) {
                body = bodyText
            }
        }

        // Execute with retry logic - pass data to recreate request
        const response = await this.fetchWithRetry(
            url,
            method,
            headers,
            body,
            options,
            requestId
        )

        // Parse response
        const responseData = await responseMiddleware(response)

        // Handle errors
        if (!response.ok) {
            await errorMiddleware(response, responseData, requestId)
        }

        return responseData as T
    }

    /**
     * Fetch with retry logic and timeout
     * Creates a fresh Request for each attempt (no body reuse issues)
     */
    private async fetchWithRetry(
        url: string,
        method: string,
        headers: Record<string, string>,
        body: BodyInit | undefined,
        options?: RequestOptions,
        requestId?: string,
        attempt = 1
    ): Promise<Response> {
        const timeout = options?.timeout ?? 30000
        const retries = options?.retries ?? 3

        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), timeout)

        try {
            logger.debug(`[${attempt}/${retries}] Fetching ${method} ${url}`, {
                requestId,
            })

            // Create fresh Request for this attempt (fix: no body reuse)
            const freshRequest = new Request(url, {
                method,
                headers,
                body,
                signal: controller.signal,
            })

            const response = await fetch(freshRequest)

            clearTimeout(timeoutId)
            return response
        } catch (error) {
            clearTimeout(timeoutId)

            const isTimeout = error instanceof Error && error.name === 'AbortError'
            const isNetwork = error instanceof TypeError

            logger.warn(
                isTimeout ? 'Request timeout' : 'Network error',
                {
                    attempt,
                    maxRetries: retries,
                    error: error instanceof Error ? error.message : String(error),
                    requestId,
                }
            )

            // Check if we should retry
            if (attempt < retries && (isTimeout || isNetwork)) {
                const delay = Math.min(1000 * Math.pow(2, attempt - 1), 10000)
                logger.debug(`Retrying in ${delay}ms...`, { requestId })

                await new Promise((resolve) => setTimeout(resolve, delay))
                return this.fetchWithRetry(
                    url,
                    method,
                    headers,
                    body,
                    options,
                    requestId,
                    attempt + 1
                )
            }

            // No more retries
            if (isTimeout) {
                throw new TimeoutError(`Request timeout after ${timeout}ms`)
            }

            if (isNetwork) {
                throw new NetworkError(
                    error instanceof Error ? error.message : 'Network request failed'
                )
            }

            throw error
        }
    }

    /**
     * GET request
     */
    async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
        return this.request<T>('GET', endpoint, undefined, options)
    }

    /**
     * POST request
     */
    async post<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
        return this.request<T>('POST', endpoint, data, options)
    }

    /**
     * PUT request
     */
    async put<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
        return this.request<T>('PUT', endpoint, data, options)
    }

    /**
     * PATCH request
     */
    async patch<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
        return this.request<T>('PATCH', endpoint, data, options)
    }

    /**
     * DELETE request
     */
    async delete<T = void>(endpoint: string, options?: RequestOptions): Promise<T> {
        return this.request<T>('DELETE', endpoint, undefined, options)
    }

    /**
     * File upload with FormData
     * Note: No retry for uploads due to FormData body consumption
     */
    async upload<T>(
        endpoint: string,
        formData: FormData,
        options?: RequestOptions
    ): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`
        const timeout = options?.timeout ?? 120000

        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), timeout)

        try {
            // Create request with FormData
            const request = new Request(url, {
                method: 'POST',
                body: formData,
                signal: controller.signal,
            })

            // Apply request middleware (will skip Content-Type for FormData)
            const enrichedRequest = await requestMiddleware(request, formData)
            const requestId = enrichedRequest.__metadata?.requestId

            logger.debug(`Uploading to ${endpoint}`, { requestId })

            const response = await fetch(enrichedRequest)

            clearTimeout(timeoutId)

            // Parse response
            const responseData = await responseMiddleware(response)

            // Handle errors
            if (!response.ok) {
                await errorMiddleware(response, responseData, requestId)
            }

            return responseData as T
        } catch (error) {
            clearTimeout(timeoutId)

            logger.error('Upload failed', {
                error: error instanceof Error ? error.message : String(error),
            })

            throw error
        }
    }

    /**
     * File download
     */
    async download(
        endpoint: string,
        filename?: string,
        options?: RequestOptions
    ): Promise<Blob> {
        const url = `${this.baseUrl}${endpoint}`
        const timeout = options?.timeout ?? 120000

        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), timeout)

        try {
            // Create request for GET
            const request = new Request(url, {
                method: 'GET',
                signal: controller.signal,
            })

            const enrichedRequest = await requestMiddleware(request)
            const requestId = enrichedRequest.__metadata?.requestId

            logger.debug(`Downloading from ${endpoint}`, { requestId })

            const response = await fetch(enrichedRequest)

            clearTimeout(timeoutId)

            if (!response.ok) {
                const errorData = await responseMiddleware(response)
                await errorMiddleware(response, errorData, requestId)
            }

            const blob = await response.blob()

            // Trigger download if filename provided
            if (filename) {
                const blobUrl = window.URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = blobUrl
                a.download = filename
                document.body.appendChild(a)
                a.click()
                window.URL.revokeObjectURL(blobUrl)
                document.body.removeChild(a)
            }

            return blob
        } catch (error) {
            clearTimeout(timeoutId)

            logger.error('Download failed', {
                error: error instanceof Error ? error.message : String(error),
            })

            throw error
        }
    }

    /**
     * Get base URL
     */
    getBaseUrl(): string {
        return this.baseUrl
    }
}

// Export singleton instance
export const api = new ApiClient(API_BASE_URL)

// Also export class and error types
export { ApiClient, ApiError, NetworkError, TimeoutError }
export type { RequestOptions }
