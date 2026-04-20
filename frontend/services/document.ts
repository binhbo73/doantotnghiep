/**
 * Document Service - Centralized document API operations
 * Based on backend Document, Folder, and Tag models
 */

import { api } from '@/services/api/client'
import { uploadService } from '@/services/upload'
import { logger } from '@/services/logger'
import type {
    Document,
    DocumentDetail,
    Folder,
    FolderDetail,
    Tag,
    ListDocumentsRequest,
    ListDocumentsResponse,
    ListFoldersRequest,
    ListFoldersResponse,
    CreateFolderRequest,
    UploadDocumentRequest,
} from '@/types/api'

/**
 * List all documents with pagination
 */
export async function listDocuments(
    params: ListDocumentsRequest
): Promise<ListDocumentsResponse> {
    const queryParams = new URLSearchParams()
    queryParams.set('limit', params.limit.toString())
    queryParams.set('offset', params.offset.toString())

    if (params.folder_id) queryParams.set('folder_id', params.folder_id)
    if (params.status) queryParams.set('status', params.status)
    if (params.file_type) queryParams.set('file_type', params.file_type)
    if (params.search) queryParams.set('search', params.search)

    const response = await api.get<ListDocumentsResponse>(
        `/documents?${queryParams.toString()}`
    )

    return response
}

/**
 * Get document details with related data
 */
export async function getDocumentDetail(documentId: string): Promise<DocumentDetail> {
    const response = await api.get<DocumentDetail>(`/documents/${documentId}`)
    return response
}

/**
 * Upload a single document
 */
export async function uploadDocument(
    file: File,
    options?: {
        folderId?: string
        accessScope?: 'personal' | 'department' | 'company'
        language?: string
        tags?: string[]
        metadata?: Record<string, unknown>
        onProgress?: (progress: number) => void
    }
): Promise<Document> {
    try {
        logger.info('Starting document upload', {
            filename: file.name,
            size: file.size,
        })

        const document = await uploadService.uploadFile(file, {
            onProgress: (progress) => {
                options?.onProgress?.(progress.percentage)
            },
        })

        logger.info('Document uploaded successfully', {
            documentId: document.id,
            filename: document.original_name,
        })

        return document
    } catch (error) {
        logger.error('Document upload failed', {
            filename: file.name,
            error: error instanceof Error ? error.message : String(error),
        })
        throw error
    }
}

/**
 * Upload multiple documents
 */
export async function uploadDocuments(
    files: File[],
    options?: {
        folderId?: string
        onProgress?: (progress: number) => void
    }
): Promise<Document[]> {
    try {
        logger.info('Starting batch upload', {
            count: files.length,
            totalSize: files.reduce((sum, f) => sum + f.size, 0),
        })

        const documents = await uploadService.uploadMultipleFiles(files, {
            onProgress: (progress) => {
                options?.onProgress?.(progress.percentage)
            },
        })

        logger.info('Batch upload completed', {
            count: documents.length,
        })

        return documents
    } catch (error) {
        logger.error('Batch upload failed', {
            error: error instanceof Error ? error.message : String(error),
        })
        throw error
    }
}

/**
 * Delete document (soft delete)
 */
export async function deleteDocument(documentId: string): Promise<void> {
    await api.delete(`/documents/${documentId}`)
    logger.info('Document deleted', { documentId })
}

/**
 * Hard delete document (permanent)
 */
export async function hardDeleteDocument(documentId: string): Promise<void> {
    await api.delete(`/documents/${documentId}?hard=true`)
    logger.info('Document hard deleted', { documentId })
}

/**
 * List folders with pagination
 */
export async function listFolders(
    params: ListFoldersRequest
): Promise<ListFoldersResponse> {
    const queryParams = new URLSearchParams()
    queryParams.set('limit', params.limit.toString())
    queryParams.set('offset', params.offset.toString())

    if (params.parent_id) queryParams.set('parent_id', params.parent_id)
    if (params.department_id) queryParams.set('department_id', params.department_id)

    const response = await api.get<ListFoldersResponse>(
        `/folders?${queryParams.toString()}`
    )

    return response
}

/**
 * Get folder details
 */
export async function getFolderDetail(folderId: string): Promise<FolderDetail> {
    const response = await api.get<FolderDetail>(`/folders/${folderId}`)
    return response
}

/**
 * Create new folder
 */
export async function createFolder(data: CreateFolderRequest): Promise<Folder> {
    const response = await api.post<Folder>('/folders', data)
    logger.info('Folder created', { folderId: response.id })
    return response
}

/**
 * Update folder
 */
export async function updateFolder(
    folderId: string,
    data: Partial<CreateFolderRequest>
): Promise<Folder> {
    const response = await api.put<Folder>(`/folders/${folderId}`, data)
    logger.info('Folder updated', { folderId })
    return response
}

/**
 * Delete folder
 */
export async function deleteFolder(folderId: string): Promise<void> {
    await api.delete(`/folders/${folderId}`)
    logger.info('Folder deleted', { folderId })
}

/**
 * List tags
 */
export async function listTags(): Promise<Tag[]> {
    const response = await api.get<Tag[]>('/tags')
    return response
}

/**
 * Create tag
 */
export async function createTag(data: {
    name: string
    color?: string
    description?: string
}): Promise<Tag> {
    const response = await api.post<Tag>('/tags', data)
    logger.info('Tag created', { tagId: response.id })
    return response
}

/**
 * Export all functions as an object for easy importing
 */
export const documentService = {
    listDocuments,
    getDocumentDetail,
    uploadDocument,
    uploadDocuments,
    deleteDocument,
    hardDeleteDocument,
    listFolders,
    getFolderDetail,
    createFolder,
    updateFolder,
    deleteFolder,
    listTags,
    createTag,
}
