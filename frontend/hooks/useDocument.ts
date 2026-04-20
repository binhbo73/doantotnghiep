/**
 * Document Hooks - React Query hooks for document operations
 * Provides server state management with caching, retries, etc.
 */

'use client'

import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query'
import { QUERY_KEYS, queryClient } from '@/lib/queryClient'
import { documentService } from '@/services/document'
import { logger } from '@/services/logger'
import type {
    Document,
    DocumentDetail,
    Folder,
    ListDocumentsRequest,
    ListDocumentsResponse,
    ListFoldersRequest,
    ListFoldersResponse,
    CreateFolderRequest,
} from '@/types/api'

// ============================================
// DOCUMENT HOOKS
// ============================================

/**
 * Hook: Fetch list of documents with pagination
 */
export function useDocuments(params: ListDocumentsRequest): UseQueryResult<ListDocumentsResponse> {
    return useQuery({
        queryKey: QUERY_KEYS.documents.list(params),
        queryFn: () => documentService.listDocuments(params),
        staleTime: 1000 * 60 * 5, // 5 minutes
        gcTime: 1000 * 60 * 10, // 10 minutes
        retry: 2,
        retryDelay: (attemptIndex: number) => Math.min(1000 * Math.pow(2, attemptIndex), 30000),
    })
}

/**
 * Hook: Fetch single document details
 */
export function useDocumentDetail(documentId: string | null): UseQueryResult<DocumentDetail> {
    return useQuery({
        queryKey: QUERY_KEYS.documents.detail(documentId || ''),
        queryFn: () => documentService.getDocumentDetail(documentId!),
        enabled: !!documentId, // Only run if documentId exists
        staleTime: 1000 * 60 * 5,
        gcTime: 1000 * 60 * 10,
    })
}

/**
 * Hook: Upload single document
 */
export function useUploadDocument() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (file: File) => documentService.uploadDocument(file),
        onSuccess: () => {
            // Revalidate documents list
            queryClient.invalidateQueries({ queryKey: QUERY_KEYS.documents.lists() })
            logger.info('Document uploaded and cache invalidated')
        },
        onError: (error: unknown) => {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error'
            logger.error('Document upload failed', { error: errorMessage })
        },
    })
}

/**
 * Hook: Upload multiple documents
 */
export function useUploadDocuments() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (files: File[]) => documentService.uploadDocuments(files),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: QUERY_KEYS.documents.lists() })
            logger.info('Documents uploaded and cache invalidated')
        },
        onError: (error: unknown) => {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error'
            logger.error('Documents upload failed', { error: errorMessage })
        },
    })
}

/**
 * Hook: Delete document
 */
export function useDeleteDocument() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (documentId: string) => documentService.deleteDocument(documentId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: QUERY_KEYS.documents.lists() })
            logger.info('Document deleted and cache invalidated')
        },
        onError: (error: unknown) => {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error'
            logger.error('Document deletion failed', { error: errorMessage })
        },
    })
}

// ============================================
// FOLDER HOOKS
// ============================================

/**
 * Hook: Fetch list of folders
 */
export function useFolders(params: ListFoldersRequest): UseQueryResult<ListFoldersResponse> {
    return useQuery({
        queryKey: QUERY_KEYS.folders.list(params),
        queryFn: () => documentService.listFolders(params),
        staleTime: 1000 * 60 * 5,
        gcTime: 1000 * 60 * 10,
    })
}

/**
 * Hook: Fetch folder details
 */
export function useFolderDetail(folderId: string | null): UseQueryResult<any> {
    return useQuery({
        queryKey: QUERY_KEYS.folders.detail(folderId || ''),
        queryFn: () => documentService.getFolderDetail(folderId!),
        enabled: !!folderId,
        staleTime: 1000 * 60 * 5,
        gcTime: 1000 * 60 * 10,
    })
}

/**
 * Hook: Create folder
 */
export function useCreateFolder() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: CreateFolderRequest) => documentService.createFolder(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: QUERY_KEYS.folders.lists() })
            logger.info('Folder created and cache invalidated')
        },
        onError: (error: unknown) => {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error'
            logger.error('Folder creation failed', { error: errorMessage })
        },
    })
}

/**
 * Hook: Delete folder
 */
export function useDeleteFolder() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (folderId: string) => documentService.deleteFolder(folderId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: QUERY_KEYS.folders.lists() })
            logger.info('Folder deleted and cache invalidated')
        },
        onError: (error: unknown) => {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error'
            logger.error('Folder deletion failed', { error: errorMessage })
        },
    })
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Manually invalidate all document queries
 */
export function invalidateDocumentQueries() {
    return queryClient.invalidateQueries({ queryKey: QUERY_KEYS.documents.all })
}

/**
 * Manually invalidate all folder queries
 */
export function invalidateFolderQueries() {
    return queryClient.invalidateQueries({ queryKey: QUERY_KEYS.folders.all })
}

/**
 * Prefetch documents for a given page
 */
export function prefetchDocuments(params: ListDocumentsRequest) {
    return queryClient.prefetchQuery({
        queryKey: QUERY_KEYS.documents.list(params),
        queryFn: () => documentService.listDocuments(params),
    })
}

/**
 * Prefetch folder details
 */
export function prefetchFolderDetail(folderId: string) {
    return queryClient.prefetchQuery({
        queryKey: QUERY_KEYS.folders.detail(folderId),
        queryFn: () => documentService.getFolderDetail(folderId),
    })
}
