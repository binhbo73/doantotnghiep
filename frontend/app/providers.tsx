/**
 * App Providers - Client-side providers for the entire app
 * Wraps app with React Query, Auth Context, etc.
 */

'use client'

import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { queryClient } from '@/lib/queryClient'
import { AuthProvider } from '@/context/index'
import { ErrorBoundary } from '@/components/error/ErrorBoundary'
import { env } from '@/config/environment'

export function Providers({ children }: { children: React.ReactNode }) {
    return (
        <ErrorBoundary>
            <QueryClientProvider client={queryClient}>
                <AuthProvider>
                    {children}
                </AuthProvider>

                {/* React Query DevTools - only in development */}
                {env.isDevelopment && <ReactQueryDevtools initialIsOpen={false} />}
            </QueryClientProvider>
        </ErrorBoundary>
    )
}
