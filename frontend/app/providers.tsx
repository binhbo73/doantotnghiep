'use client'

/**
 * App Providers - Client-side providers for the entire app
 * Wraps app with React Query, Auth Context, etc.
 */



import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/lib/queryClient'
import { AuthProvider } from '@/context/index'
import { ErrorBoundary } from '@/components/error/ErrorBoundary'
import { Toaster } from 'sonner'

export function Providers({ children }: { children: React.ReactNode }) {
    return (
        <ErrorBoundary>
            <QueryClientProvider client={queryClient}>
                <AuthProvider>
                    {children}
                    <Toaster position="top-right" expand={true} richColors closeButton />
                </AuthProvider>
            </QueryClientProvider>
        </ErrorBoundary>
    )
}
