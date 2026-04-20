/**
 * Error Middleware - Centralized error handling
 * Handle status codes, log errors, notify user
 */

import { logger } from '@/services/logger'
import { ApiError, ValidationError } from '@/services/api/errors'
import type { ApiErrorSchema } from '@/types/api'

interface ErrorResponse {
    error?: string
    message?: string
    status?: number
    details?: unknown
    errors?: Record<string, string[]>
    timestamp?: string
    request_id?: string
}

/**
 * Handle API errors with specific status codes
 */
export async function errorMiddleware(
    response: Response,
    errorData: unknown,
    requestId?: string
): Promise<void> {
    const status = response.status
    const errorObj = errorData as ErrorResponse | null

    // Log error
    const errorInfo = {
        status,
        url: response.url,
        requestId,
        error: errorObj?.error || errorObj?.message,
        details: errorObj?.details,
        timestamp: new Date().toISOString(),
    }

    logger.error(`API Error [${status}]`, errorInfo)

    // Handle specific status codes
    switch (status) {
        case 400:
            // Bad Request - validation error
            if (errorObj?.errors) {
                throw new ValidationError(
                    errorObj.message || 'Validation error',
                    errorObj.errors
                )
            }
            throw new ApiError(
                status,
                errorObj?.message || 'Bad Request',
                errorObj?.details,
                requestId
            )

        case 401:
            // Unauthorized - distinguish between invalid credentials and session expired
            const message = errorObj?.message || ''
            const lowerMessage = message.toLowerCase()

            // Check for credential-related keywords (both English and Vietnamese)
            const isInvalidCredentials =
                lowerMessage.includes('password') ||
                lowerMessage.includes('credentials') ||
                lowerMessage.includes('mật khẩu') ||
                lowerMessage.includes('email') ||
                lowerMessage.includes('username') ||
                lowerMessage.includes('không chính xác') ||
                lowerMessage.includes('invalid')

            // Only clear auth tokens if NOT a credentials error (don't clear on wrong password)
            if (!isInvalidCredentials) {
                localStorage.removeItem('auth_token')
                localStorage.removeItem('refresh_token')
                window.dispatchEvent(new CustomEvent('auth:unauthorized'))
            }

            // Use backend message if it's about credentials, otherwise show session expired
            const errorMessage = isInvalidCredentials
                ? message
                : 'Session expired. Please login again.'

            throw new ApiError(
                status,
                errorMessage,
                errorObj,
                requestId
            )

        case 403:
            // Forbidden - user doesn't have permission
            window.dispatchEvent(new CustomEvent('auth:forbidden'))

            throw new ApiError(
                status,
                'You do not have permission to perform this action.',
                errorObj,
                requestId
            )

        case 404:
            // Not Found
            throw new ApiError(
                status,
                errorObj?.message || 'Resource not found',
                errorObj,
                requestId
            )

        case 409:
            // Conflict - usually data conflict
            throw new ApiError(
                status,
                errorObj?.message || 'Data conflict',
                errorObj,
                requestId
            )

        case 422:
            // Unprocessable Entity - validation
            if (errorObj?.errors) {
                throw new ValidationError(
                    errorObj.message || 'Validation error',
                    errorObj.errors
                )
            }
            throw new ApiError(
                status,
                errorObj?.message || 'Unprocessable Entity',
                errorObj,
                requestId
            )

        case 429:
            // Too Many Requests - rate limited
            throw new ApiError(
                status,
                'Too many requests. Please try again later.',
                errorObj,
                requestId
            )

        case 500:
        case 502:
        case 503:
        case 504:
            // Server errors
            logger.error(`Server Error [${status}]`, {
                url: response.url,
                message: errorObj?.message,
                requestId,
            })

            throw new ApiError(
                status,
                'Server error. Please try again later.',
                errorObj,
                requestId
            )

        default:
            // Generic error
            throw new ApiError(
                status,
                errorObj?.message || `HTTP Error ${status}`,
                errorObj,
                requestId
            )
    }
}

/**
 * Format error for display to user
 */
export function formatErrorForUser(error: unknown): string {
    if (error instanceof ApiError) {
        return error.message
    }

    if (error instanceof ValidationError) {
        // For validation errors, show first error message
        if (error.errors) {
            const firstField = Object.keys(error.errors)[0]
            const firstError = error.errors[firstField]?.[0]
            return firstError || 'Validation error'
        }
        return error.message
    }

    if (error instanceof Error) {
        return error.message
    }

    return 'An unexpected error occurred'
}

/**
 * Check if error is retriable
 */
export function isRetriableError(error: unknown): boolean {
    if (error instanceof ApiError) {
        // Retry on 5xx errors
        return error.statusCode >= 500
    }

    return false
}
