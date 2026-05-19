/**
 * API URL helpers
 * Use same-origin API paths in the browser so requests go through Next.js rewrites.
 */

const DEFAULT_BACKEND_ORIGIN = 'http://localhost:8000'
const DEFAULT_API_PATH = '/api/v1'

function normalizeTrailingSlash(value: string): string {
    return value.replace(/\/$/, '')
}

function normalizeEndpoint(endpoint: string): string {
    return endpoint.startsWith('/') ? endpoint : `/${endpoint}`
}

export function getApiBaseUrl(): string {
    const configuredUrl = process.env.NEXT_PUBLIC_API_URL?.trim()

    if (typeof window !== 'undefined') {
        return configuredUrl?.startsWith('/') ? normalizeTrailingSlash(configuredUrl) : DEFAULT_API_PATH
    }

    if (configuredUrl) {
        return normalizeTrailingSlash(configuredUrl)
    }

    return `${DEFAULT_BACKEND_ORIGIN}${DEFAULT_API_PATH}`
}

export function buildApiUrl(endpoint: string): string {
    return `${getApiBaseUrl()}${normalizeEndpoint(endpoint)}`
}

export function getDirectApiBaseUrl(): string {
    const configuredUrl = process.env.NEXT_PUBLIC_API_URL?.trim()

    if (configuredUrl && !configuredUrl.startsWith('/')) {
        return normalizeTrailingSlash(configuredUrl)
    }

    if (typeof window !== 'undefined') {
        return `${window.location.protocol}//${window.location.hostname}:8000${DEFAULT_API_PATH}`
    }

    return `${DEFAULT_BACKEND_ORIGIN}${DEFAULT_API_PATH}`
}

export function buildDirectApiUrl(endpoint: string): string {
    return `${getDirectApiBaseUrl()}${normalizeEndpoint(endpoint)}`
}
