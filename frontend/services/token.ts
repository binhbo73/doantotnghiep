/**
 * Token Management - Auth token lifecycle for API requests
 * 
 * Strategy:
 * 1. Initialize with placeholder on app load (non-blocking)
 * 2. Use loginAndGetToken() to get real JWT from backend
 * 3. Store in localStorage for persistence
 */

const TOKEN_KEY = 'auth_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

/**
 * Initialize token on app startup (non-blocking)
 * Sets placeholder if no existing token
 */
export function initializeToken(): void {
    if (typeof window === 'undefined') return

    try {
        const existing = localStorage.getItem(TOKEN_KEY)
        if (existing && existing !== '') {
            console.log('✅ Token already in localStorage')
            return
        }

        // Placeholder - will be replaced after real login
        const placeholder = 'placeholder-' + Date.now()
        localStorage.setItem(TOKEN_KEY, placeholder)
        console.log('ℹ️ Placeholder token initialized. Call loginAndGetToken() to get real JWT.')
    } catch (err) {
        console.error('❌ Error initializing token:', err)
    }
}

/**
 * Login to backend and get real JWT token
 * Call this after user submits login form or on debug page
 *
 * @param username - Login username
 * @param password - Login password
 * @returns JWT token if successful
 */
export async function loginAndGetToken(username: string, password: string): Promise<string> {
    try {
        console.log(`🔐 Logging in as "${username}"...`)

        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
            signal: AbortSignal.timeout(10000) // 10 second timeout
        })

        console.log(`📡 Login response status: ${response.status}`)

        if (!response.ok) {
            const errorText = await response.text()
            console.error(`❌ Login failed (${response.status}): ${errorText.substring(0, 300)}`)
            throw new Error(`Login failed with status ${response.status}`)
        }

        const data = await response.json()
        console.log(`📡 Login response data keys: ${Object.keys(data || {}).join(', ')}`)
        console.log(`📡 Login data.data keys: ${Object.keys(data?.data || {}).join(', ')}`)

        // Try multiple possible response formats
        const token = data?.data?.access_token || data?.access_token || data?.token
        const refreshToken = data?.data?.refresh_token || data?.refresh_token

        if (!token) {
            console.error('❌ No access_token in login response:', JSON.stringify(data).substring(0, 500))
            throw new Error('No token in login response')
        }

        if (!refreshToken) {
            console.error('❌ No refresh_token in login response! Data:', JSON.stringify(data?.data || {}).substring(0, 500))
        }

        // Store both access and refresh tokens
        if (typeof window !== 'undefined') {
            localStorage.setItem(TOKEN_KEY, token)
            console.log(`✅ Access token stored (length: ${token.length})`)

            if (refreshToken) {
                localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
                console.log(`✅ Refresh token stored (length: ${refreshToken.length})`)
            } else {
                console.warn('⚠️ No refresh_token to store!')
            }

            // Verify storage
            const storedAccess = localStorage.getItem(TOKEN_KEY)
            const storedRefresh = localStorage.getItem(REFRESH_TOKEN_KEY)
            console.log(`🔍 Verified storage - access: ${storedAccess ? '✅' : '❌'}, refresh: ${storedRefresh ? '✅' : '❌'}`)
        }

        console.log('✅ Access token obtained and stored successfully')
        return token
    } catch (err) {
        console.error('❌ Login error:', err)
        throw err
    }
}

/**
 * Get current token from localStorage (sync)
 * Used by API client to attach to requests
 */
export function getAuthTokenForAPI(): string {
    if (typeof window === 'undefined') return ''

    try {
        const token = localStorage.getItem(TOKEN_KEY) || ''

        // Log token status
        if (token.includes('placeholder')) {
            console.warn('⚠️ Using placeholder token - real JWT not yet obtained. Run loginAndGetToken()')
        }

        return token
    } catch (err) {
        console.error('❌ Error retrieving token:', err)
        return ''
    }
}

/**
 * Store token in localStorage
 */
export function setAuthToken(token: string): void {
    if (typeof window === 'undefined') return

    try {
        localStorage.setItem(TOKEN_KEY, token)
        console.log('✅ Token stored')
    } catch (err) {
        console.error('❌ Error storing token:', err)
    }
}

/**
 * Get refresh token from localStorage
 */
export function getRefreshToken(): string {
    if (typeof window === 'undefined') return ''

    try {
        return localStorage.getItem(REFRESH_TOKEN_KEY) || ''
    } catch (err) {
        console.error('❌ Error retrieving refresh token:', err)
        return ''
    }
}

/**
 * Clear all tokens on logout
 */
export function clearAuthToken(): void {
    if (typeof window === 'undefined') return

    try {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(REFRESH_TOKEN_KEY)
        console.log('✅ Tokens cleared on logout')
    } catch (err) {
        console.error('❌ Error clearing tokens:', err)
    }
}

/**
 * Logout from backend and clear local tokens
 * Call this when user clicks logout button
 *
 * Sends: Authorization header with access_token + refresh_token in body
 */
export async function logoutUser(): Promise<void> {
    try {
        const accessToken = getAuthTokenForAPI()
        const refreshToken = getRefreshToken()

        console.log(`🔓 Logout attempt:`)
        console.log(`  - Access token: ${accessToken ? `✅ (length: ${accessToken.length})` : '❌ EMPTY'}`)
        console.log(`  - Refresh token: ${refreshToken ? `✅ (length: ${refreshToken.length})` : '❌ EMPTY'}`)

        if (!accessToken || accessToken.includes('placeholder')) {
            console.warn('⚠️ No valid access token to logout with')
            clearAuthToken()
            return
        }

        if (!refreshToken) {
            console.warn('⚠️ No refresh token found! Checking localStorage directly...')
            const directRefresh = localStorage.getItem(REFRESH_TOKEN_KEY)
            console.warn(`  - Direct localStorage lookup: ${directRefresh ? `✅ (length: ${directRefresh.length})` : '❌ EMPTY'}`)
        }

        console.log('📡 Sending logout request...')
        console.log(`   Body: { "refresh_token": "${refreshToken ? refreshToken.substring(0, 20) + '...' : 'EMPTY'}" }`)
        console.log(`   Header: Authorization: Bearer ${accessToken.substring(0, 20)}...`)

        const response = await fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({
                refresh: refreshToken
            }),
            signal: AbortSignal.timeout(5000)
        })

        console.log(`📡 Logout response status: ${response.status}`)

        try {
            const responseData = await response.text()
            console.log(`📡 Logout response: ${responseData.substring(0, 300)}`)
        } catch (e) {
            // Ignore text parsing errors
        }

        if (!response.ok) {
            console.error(`❌ Logout API returned ${response.status}`)
        } else {
            console.log('✅ Logout API returned 200 OK')
        }

        clearAuthToken()
        console.log('✅ Logged out successfully and tokens cleared')
    } catch (err) {
        console.error('❌ Logout error:', err)
        clearAuthToken()
    }
}

