/**
 * Request Middleware - Transform outgoing requests
 * Add auth token, headers, request ID for tracking
 */

import { getAuthToken } from '@/services/auth'

interface RequestMetadata {
    requestId: string
    timestamp: string
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

    // Add auth header if token exists
    if (token) {
        request.headers.set('Authorization', `Bearer ${token}`)
    }

    // Add body for non-GET requests
    if (data && request.method !== 'GET' && request.method !== 'HEAD') {
        try {
            // Only set Content-Type for JSON (not for FormData)
            if (!(data instanceof FormData)) {
                request.headers.set('Content-Type', 'application/json')
                request = new Request(request, {
                    body: JSON.stringify(data),
                })
            }
        } catch (err) {
            console.error('Error in request middleware:', err)
            throw err
        }
    }

    // Attach metadata for later use
    const enrichedRequest = request as Request & { __metadata?: RequestMetadata }
    enrichedRequest.__metadata = { requestId, timestamp }

    return enrichedRequest
}
