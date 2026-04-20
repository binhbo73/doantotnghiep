// Example component showing API integration
'use client'

import { useEffect, useState } from 'react'
import { api } from '@/services/api'
import { authService } from '@/services/auth'
import { useApi } from '@/hooks/useApi'

export function ApiExampleComponent() {
    const [statusMessage, setStatusMessage] = useState('Testing API connection...')
    const { request, loading, data } = useApi()

    useEffect(() => {
        const testConnections = async () => {
            try {
                // Test 1: Health check (no auth needed)
                const healthResponse = await api.get('/health')
                console.log('✅ Health Check:', healthResponse)

                // Test 2: Check auth
                if (authService.isAuthenticated()) {
                    console.log('✅ User is authenticated')
                    const token = authService.getToken()
                    console.log('Token:', token?.substring(0, 20) + '...')
                } else {
                    console.log('ℹ️  User is not authenticated')
                }

                setStatusMessage('✅ All systems ready! Check console for details.')
            } catch (error) {
                const errorMsg = error instanceof Error ? error.message : 'Unknown error'
                console.error('❌ API Error:', errorMsg)
                setStatusMessage(`❌ Error: ${errorMsg}`)
            }
        }

        testConnections()
    }, [])

    const handleTestRequest = async () => {
        try {
            const result = await request('/documents', 'GET')
            console.log('Fetched documents:', result)
        } catch (error) {
            console.error('Request failed:', error)
        }
    }

    return (
        <div style={{ padding: '2rem', fontFamily: 'monospace' }}>
            <h2>API Integration Test</h2>

            <div style={{ marginBottom: '1rem', padding: '1rem', backgroundColor: '#f0f0f0' }}>
                <p>{statusMessage}</p>
            </div>

            <div style={{ marginBottom: '1rem' }}>
                <button
                    onClick={handleTestRequest}
                    disabled={loading}
                    style={{
                        padding: '0.5rem 1rem',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        opacity: loading ? 0.5 : 1,
                    }}
                >
                    {loading ? 'Loading...' : 'Test GET Request'}
                </button>
            </div>

            {data && (
                <pre
                    style={{
                        backgroundColor: '#f5f5f5',
                        padding: '1rem',
                        borderRadius: '4px',
                        overflow: 'auto',
                        maxHeight: '300px',
                    }}
                >
                    {JSON.stringify(data, null, 2)}
                </pre>
            )}

            <div style={{ marginTop: '2rem', fontSize: '0.9rem', color: '#666' }}>
                <h3>Setup Checklist:</h3>
                <ul>
                    <li>✅ API Client initialized with retry logic</li>
                    <li>✅ Error handling (ApiError, NetworkError, TimeoutError)</li>
                    <li>✅ Authentication token management</li>
                    <li>✅ Custom hooks (useApi, useAuth)</li>
                    <li>✅ Specialized services (auth, chat, document)</li>
                    <li>✅ Middleware for protected routes</li>
                    <li>ℹ️ Ready to start building features!</li>
                </ul>
            </div>
        </div>
    )
}
