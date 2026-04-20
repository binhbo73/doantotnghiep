/**
 * Environment Configuration
 * Centralized configuration with validation
 */

type Environment = 'development' | 'production'
type LogLevel = 'debug' | 'info' | 'warn' | 'error'

// Validate required environment variables
function validateEnv(): void {
    const required = ['NEXT_PUBLIC_API_URL']
    const missing = required.filter((key) => !process.env[key])

    if (missing.length > 0) {
        throw new Error(
            `Missing required environment variables: ${missing.join(', ')}\n` +
            `Please check your .env.local file`
        )
    }
}

// Run validation in non-server environments
if (typeof window !== 'undefined' || process.env.NODE_ENV !== 'production') {
    // Validation can be deferred for SSR
}

export const env = Object.freeze({
    // API Configuration
    apiUrl: (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').replace(
        /\/$/, // Remove trailing slash
        ''
    ),

    // Environment
    environment: (process.env.NODE_ENV || 'development') as Environment,
    isDevelopment: process.env.NODE_ENV === 'development',
    isProduction: process.env.NODE_ENV === 'production',

    // Logging
    logLevel: (process.env.NEXT_PUBLIC_LOG_LEVEL || 'info') as LogLevel,
    logToBackend: process.env.NEXT_PUBLIC_LOG_TO_BACKEND !== 'false',

    // Feature Flags
    enableOfflineMode: process.env.NEXT_PUBLIC_ENABLE_OFFLINE !== 'false',
    enableErrorTracking: process.env.NEXT_PUBLIC_ERROR_TRACKING === 'true',
    enableAnalytics: process.env.NEXT_PUBLIC_ANALYTICS === 'true',

    // Request Configuration
    defaultTimeout: parseInt(process.env.NEXT_PUBLIC_DEFAULT_TIMEOUT || '30000'),
    uploadTimeout: parseInt(process.env.NEXT_PUBLIC_UPLOAD_TIMEOUT || '120000'),
    maxRetries: parseInt(process.env.NEXT_PUBLIC_MAX_RETRIES || '3'),

    // Cache Configuration
    cacheStaleTime: parseInt(process.env.NEXT_PUBLIC_CACHE_STALE_TIME || '300000'), // 5 minutes
    cacheGcTime: parseInt(process.env.NEXT_PUBLIC_CACHE_GC_TIME || '600000'), // 10 minutes

    // UI Configuration
    itemsPerPage: parseInt(process.env.NEXT_PUBLIC_ITEMS_PER_PAGE || '20'),
    maxUploadSize: parseInt(process.env.NEXT_PUBLIC_MAX_UPLOAD_SIZE || '104857600'), // 100MB

    // Sentry Configuration (for error tracking)
    sentryDsn: process.env.NEXT_PUBLIC_SENTRY_DSN || '',
    sentryEnabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN,

    // Version
    appVersion: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
})

/**
 * Utility function to validate config at runtime
 */
export function validateConfig(): void {
    if (!env.apiUrl) {
        throw new Error('API URL is not configured')
    }

    if (env.defaultTimeout <= 0) {
        throw new Error('Default timeout must be positive')
    }

    if (env.itemsPerPage <= 0) {
        throw new Error('Items per page must be positive')
    }
}

/**
 * Get full API endpoint URL
 */
export function getApiUrl(endpoint: string): string {
    const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
    return `${env.apiUrl}${normalizedEndpoint}`
}

/**
 * Check if in development mode
 */
export function isDev(): boolean {
    return env.isDevelopment
}

/**
 * Check if in production mode
 */
export function isProd(): boolean {
    return env.isProduction
}

/**
 * Get log level
 */
export function getLogLevel(): LogLevel {
    return env.logLevel
}

/**
 * Export type for usage in other files
 */
export type { Environment, LogLevel }
