/**
 * React Query Configuration
 * Centralized setup for TanStack Query (formerly React Query)
 */

import { QueryClient, DefaultOptions } from '@tanstack/react-query'
import { logger } from '@/services/logger'

const queryConfig: DefaultOptions = {
    queries: {
        // How long data is fresh (not stale)
        staleTime: 1000 * 60 * 5, // 5 minutes
        // How long to keep cache after no subscribers
        gcTime: 1000 * 60 * 10, // 10 minutes (formerly cacheTime)
        // Automatic retry configuration
        retry: (failureCount: number, error: unknown) => {
            // Don't retry on 4xx errors
            if (error instanceof Error && error.message.includes('HTTP 4')) {
                return false
            }
            // Retry up to 3 times for network errors
            return failureCount < 3
        },
        retryDelay: (attemptIndex: number) => {
            // Exponential backoff: 1s, 2s, 4s, max 30s
            return Math.min(1000 * Math.pow(2, attemptIndex), 30000)
        },
        // Refetch on window focus (useful for multiwindow apps)
        refetchOnWindowFocus: true,
        // Refetch on mount if stale
        refetchOnMount: true,
        // Refetch on reconnect
        refetchOnReconnect: true,
    },
    mutations: {
        // Same retry logic for mutations
        retry: 1,
        retryDelay: (attemptIndex: number) => {
            return Math.min(1000 * Math.pow(2, attemptIndex), 30000)
        },
    },
}

export const queryClient = new QueryClient({
    defaultOptions: queryConfig,
})

// Optional: Add global error handling
queryClient.setDefaultOptions({
    queries: {
        ...queryConfig.queries,
    },
    mutations: {
        ...queryConfig.mutations,
    },
})

/**
 * Custom hooks for common query operations
 */

export const QUERY_KEYS = {
    // Documents
    documents: {
        all: ['documents'] as const,
        lists: () => [...QUERY_KEYS.documents.all, 'list'] as const,
        list: (params: Record<string, unknown>) =>
            [...QUERY_KEYS.documents.lists(), params] as const,
        details: () => [...QUERY_KEYS.documents.all, 'detail'] as const,
        detail: (id: string) => [...QUERY_KEYS.documents.details(), id] as const,
    },

    // Folders
    folders: {
        all: ['folders'] as const,
        lists: () => [...QUERY_KEYS.folders.all, 'list'] as const,
        list: (params: Record<string, unknown>) =>
            [...QUERY_KEYS.folders.lists(), params] as const,
        details: () => [...QUERY_KEYS.folders.all, 'detail'] as const,
        detail: (id: string) => [...QUERY_KEYS.folders.details(), id] as const,
    },

    // Messages
    messages: {
        all: ['messages'] as const,
        lists: () => [...QUERY_KEYS.messages.all, 'list'] as const,
        list: (conversationId: string, params: Record<string, unknown>) =>
            [...QUERY_KEYS.messages.lists(), conversationId, params] as const,
    },

    // Conversations
    conversations: {
        all: ['conversations'] as const,
        lists: () => [...QUERY_KEYS.conversations.all, 'list'] as const,
        details: () => [...QUERY_KEYS.conversations.all, 'detail'] as const,
        detail: (id: string) => [...QUERY_KEYS.conversations.details(), id] as const,
    },

    // Auth
    auth: {
        all: ['auth'] as const,
        profile: () => [...QUERY_KEYS.auth.all, 'profile'] as const,
        me: () => [...QUERY_KEYS.auth.all, 'me'] as const,
    },

    // Search
    search: {
        all: ['search'] as const,
        list: (query: string) => [...QUERY_KEYS.search.all, query] as const,
    },
} as const

/**
 * Helper function to invalidate multiple query keys at once
 */
export async function invalidateQueries(keys: readonly unknown[][]) {
    await Promise.all(
        keys.map((key) => queryClient.invalidateQueries({ queryKey: key as any }))
    )
}
