/**
 * Folder Service - API calls for folder management
 * 
 * Endpoints:
 *   GET /api/v1/folders               → All folders
 *   GET /api/v1/folders/:id/documents → Documents in a folder
 */

import { api } from './api'

// ─── Types ───────────────────────────────────────────────────
export interface FolderResponse {
    id: string
    name: string
    description: string | null
    parent_id: string | null
    department_id: string | null
    access_scope: string
    metadata: Record<string, unknown>
    created_by_id: string | null
    is_deleted: boolean
    deleted_at: string | null
    created_at: string
    updated_at: string
    // Bổ sung các trường hỗ trợ dạng Tree và đếm số lượng
    sub_folders?: FolderResponse[]
    subfolder_count?: number
    document_count?: number
}

export interface FolderDocumentResponse {
    id: string
    original_name: string
    file_type: string
    file_size: number
    status: 'pending' | 'processing' | 'completed' | 'failed'
    // API trả về field names không có _id suffix
    uploader: string | null        // uploader UUID
    uploader_name: string | null
    folder: string | null          // folder UUID
    folder_name: string | null
    department: string | null      // department UUID
    access_scope: 'personal' | 'company' | 'department' | string
    tags_list: string[]
    is_deleted: boolean
    created_at: string
    updated_at: string
    // Backward compat aliases (được map thủ công nếu cần)
    folder_id?: string | null
    department_id?: string | null
    uploader_id?: string | null
    [key: string]: unknown
}

export interface PaginationInfo {
    page: number
    page_size: number
    total_items: number
    total_pages: number
    has_next: boolean
    has_prev: boolean
}

// ─── API Calls ───────────────────────────────────────────────

/**
 * Fetch all folders
 * GET /api/v1/folders
 */
export async function fetchAllFolders(): Promise<FolderResponse[]> {
    try {
        const response = await api.get<any>('/folders')

        console.log('📁 Folders API Response:', JSON.stringify(response, null, 2).substring(0, 800))

        // Handle different response formats from backend
        if (Array.isArray(response)) {
            return response
        }

        // { data: [...] } or { data: { items: [...] } }
        if (response?.data) {
            if (Array.isArray(response.data)) {
                return response.data
            }
            if (Array.isArray(response.data?.items)) {
                return response.data.items
            }
        }

        // { items: [...] }
        if (Array.isArray(response?.items)) {
            return response.items
        }

        console.warn('⚠️ Unexpected folders response format:', response)
        return []
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch folders'
        console.error('❌ Error fetching folders:', err)
        throw new Error(message)
    }
}

/**
 * Fetch documents in a specific folder
 * GET /api/v1/folders/:folderId/documents?page=1&page_size=20
 */
export async function fetchFolderDocuments(
    folderId: string,
    params?: { page?: number; page_size?: number }
): Promise<{ items: FolderDocumentResponse[]; pagination: PaginationInfo | null }> {
    try {
        const page = params?.page || 1
        const pageSize = params?.page_size || 20

        const response = await api.get<any>(
            `/folders/${folderId}/documents?page=${page}&page_size=${pageSize}`
        )

        console.log(`📄 Folder ${folderId} Documents Response:`, JSON.stringify(response, null, 2).substring(0, 800))

        // Handle different response formats
        let items: FolderDocumentResponse[] = []
        let pagination: PaginationInfo | null = null

        if (Array.isArray(response)) {
            items = response
        } else if (response?.data) {
            if (Array.isArray(response.data)) {
                items = response.data
            } else if (Array.isArray(response.data?.items)) {
                items = response.data.items
                pagination = response.data.pagination || null
            }
        } else if (Array.isArray(response?.items)) {
            items = response.items
            pagination = response.pagination || null
        }

        return { items, pagination }
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch folder documents'
        console.error(`❌ Error fetching documents for folder ${folderId}:`, err)
        throw new Error(message)
    }
}

/**
 * Fetch all documents (includes documents not assigned to any folder)
 * GET /api/v1/documents?page=1&page_size=100
 */
export async function fetchAllDocuments(
    params?: { page?: number; page_size?: number }
): Promise<{ items: FolderDocumentResponse[]; pagination: PaginationInfo | null }> {
    try {
        const page = params?.page || 1
        const pageSize = params?.page_size || 100

        const response = await api.get<any>(`/documents?page=${page}&page_size=${pageSize}`)

        console.log('📄 All Documents Response:', JSON.stringify(response, null, 2).substring(0, 800))

        // Handle different response formats
        let items: FolderDocumentResponse[] = []
        let pagination: PaginationInfo | null = null

        if (Array.isArray(response)) {
            items = response
        } else if (response?.data) {
            if (Array.isArray(response.data)) {
                items = response.data
            } else if (Array.isArray(response.data?.items)) {
                items = response.data.items
                pagination = response.data.pagination || null
            }
        } else if (Array.isArray(response?.items)) {
            items = response.items
            pagination = response.pagination || null
        }

        return { items, pagination }
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch all documents'
        console.error('❌ Error fetching all documents:', err)
        throw new Error(message)
    }
}
