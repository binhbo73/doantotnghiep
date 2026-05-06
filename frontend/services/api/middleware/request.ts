/**
 * Request Middleware - Transform outgoing requests
 * Add auth token, headers, request ID for tracking
 */

import { getAuthToken } from '@/services/auth'

interface RequestMetadata {
    requestId: string
    timestamp: string
}

// Public endpoints that don't require auth token
const PUBLIC_ENDPOINTS = [
    '/auth/login',
    '/auth/register',
    '/auth/forgot-password',
    '/auth/reset-password',
    '/auth/refresh',
    '/health',
]

function isPublicEndpoint(url: string): boolean {
    return PUBLIC_ENDPOINTS.some(endpoint => url.includes(endpoint))
}

export async function requestMiddleware(
    request: Request,
    data?: unknown
): Promise<Request & { __metadata?: RequestMetadata }> {
    // Generate request ID for tracking
    const requestId = crypto.randomUUID()
    const timestamp = new Date().toISOString()

    // Get auth token
    const token = getAuthToken()

    // Add headers
    request.headers.set('X-Request-ID', requestId)
    request.headers.set('X-API-Version', '1.0')
    request.headers.set('X-Timestamp', timestamp)

    // Add auth header if token exists (but filter out placeholder tokens)
    if (token && !token.includes('placeholder')) {
        request.headers.set('Authorization', `Bearer ${token}`)
        console.log(`✅ [RequestMiddleware] Authorization header added for ${request.method} ${request.url} (token length: ${token.length})`)
    } else if (token && token.includes('placeholder')) {
        console.warn(`⚠️ [RequestMiddleware] Placeholder token found for ${request.method} ${request.url} - no real JWT yet. User not authenticated.`)
    } else if (!isPublicEndpoint(request.url)) {
        // Only warn about missing tokens for protected endpoints
        console.warn(`⚠️ [RequestMiddleware] No auth token found for ${request.method} ${request.url}. localStorage check:`, {
            storageName: typeof window !== 'undefined' ? (typeof localStorage !== 'undefined' ? 'available' : 'unavailable') : 'server-side',
            tokenValue: token ? 'exists' : 'null/empty'
        })
    }

    // Add body for non-GET requests
    if (data && request.method !== 'GET' && request.method !== 'HEAD') {
        try {
            // Only set Content-Type for JSON (not for FormData)
            if (!(data instanceof FormData)) {
                const jsonBody = JSON.stringify(data)
                request.headers.set('Content-Type', 'application/json')
                request = new Request(request, {
                    body: jsonBody,
                })

                console.log(`📡 [RequestMiddleware] Request body:`, jsonBody)
                console.log(`📡 [RequestMiddleware] Request URL: ${request.url}`)
                console.log(`📡 [RequestMiddleware] Request method: ${request.method}`)
            }
        } catch (err) {
            console.error('❌ [RequestMiddleware] Error in request middleware:', err)
            throw err
        }
    }

    // Attach metadata for later use
    const enrichedRequest = request as Request & { __metadata?: RequestMetadata }
    enrichedRequest.__metadata = { requestId, timestamp }

    return enrichedRequest
}
