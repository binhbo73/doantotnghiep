/**
 * Folder Service - API calls for folder management
 * 
 * Endpoints:
 *   GET /api/v1/folders               → All folders
 *   GET /api/v1/folders/:id/documents → Documents in a folder
 */

import { api, ApiError } from './api'

// ─── Types ───────────────────────────────────────────────────
export interface FolderResponse {
    id: string
    name: string
    description: string | null
    parent_id: string | null
    department_id: string | null
    access_scope: 'company' | 'department' | 'personal'
    metadata: Record<string, unknown>
    created_by_id: string | null
    uploader_name?: string | null
    is_deleted: boolean
    deleted_at: string | null
    my_permission: 'delete' | 'write' | 'read' | 'none'
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
    filename?: string
    file_type: string
    file_size: number
    status: 'pending' | 'processing' | 'completed' | 'failed'
    // API trả về field names không có _id suffix
    uploader: string | null        // uploader UUID
    uploader_name: string | null
    folder: string | null          // folder UUID
    folder_name: string | null
    department: string | null      // department UUID
    access_scope: 'personal' | 'company' | 'department'
    my_permission: 'delete' | 'write' | 'read' | 'none'
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
        if (err instanceof ApiError) {
            throw err
        }
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
        if (err instanceof ApiError) {
            throw err
        }
        throw new Error(message)
    }
}

/**
 * Fetch all documents (includes documents not assigned to any folder)
 * GET /api/v1/documents?page=1&page_size=100
 */
export async function fetchAllDocuments(
    params?: { page?: number; page_size?: number; access_scope?: 'personal' | 'department' | 'company' }
): Promise<{ items: FolderDocumentResponse[]; pagination: PaginationInfo | null }> {
    try {
        const page = params?.page || 1
        const pageSize = params?.page_size || 100
        const accessScopeQuery = params?.access_scope ? `&access_scope=${params.access_scope}` : ''

        const response = await api.get<any>(`/documents?page=${page}&page_size=${pageSize}${accessScopeQuery}`)

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
        if (err instanceof ApiError) {
            throw err
        }
        throw new Error(message)
    }
}

// ─── Types for Organized Data ─────────────────────────────────
export interface FolderWithDocuments extends FolderResponse {
    documents: FolderDocumentResponse[]
}

export interface PersonalDocumentsOrganized {
    folders: FolderWithDocuments[]
    unfoldered_documents: FolderDocumentResponse[]
}

/**
 * Fetch personal folders and documents organized by folder
 */
export async function fetchPersonalFoldersWithDocuments(
    accessScope: 'personal' | 'department' | 'company' = 'personal'
): Promise<PersonalDocumentsOrganized> {
    try {
        console.log(`🔍 [START] Fetching ${accessScope} folders and documents...`)

        // Fetch all folders
        const allFolders = await fetchAllFolders()
        console.log(`📁 Total folders fetched:`, allFolders.length)
        console.log(`📁 All folders data:`, JSON.stringify(allFolders.slice(0, 2), null, 2))

        // Filter by access_scope
        const folders = allFolders.filter(f => {
            const match = f.access_scope === accessScope
            if (!match) {
                console.log(`⏭️  Folder "${f.name}" has access_scope="${f.access_scope}" (skip)`)
            }
            return match
        })
        console.log(`✅ Filtered folders for "${accessScope}":`, folders.length)

        // Helper function to fetch all pages
        const fetchAllPages = async (
            fetchFn: (params: any) => Promise<{ items: FolderDocumentResponse[]; pagination: PaginationInfo | null }>,
            params: any,
            context: string
        ): Promise<FolderDocumentResponse[]> => {
            let allItems: FolderDocumentResponse[] = []
            let page = 1
            let hasNext = true

            while (hasNext) {
                try {
                    console.log(`📄 Fetching ${context} page ${page}...`)
                    const { items, pagination } = await fetchFn({ ...params, page, page_size: 100 })
                    allItems.push(...items)
                    console.log(`📄 Got ${items.length} items, has_next=${pagination?.has_next}`)
                    hasNext = pagination?.has_next ?? false
                    page += 1
                } catch (err) {
                    console.warn(`⚠️ Error fetching ${context} page ${page}:`, err)
                    hasNext = false
                }
            }

            console.log(`✅ ${context}: Total items fetched: ${allItems.length}`)
            return allItems
        }

        // Fetch documents by folder
        const foldersWithDocuments: FolderWithDocuments[] = []

        for (const folder of folders) {
            try {
                console.log(`\n📂 Processing folder: "${folder.name}" (${folder.id})`)
                const documents = await fetchAllPages(
                    (params) => fetchFolderDocuments(folder.id, params),
                    { page: 1 },
                    `Folder "${folder.name}"`
                )

                const filtered = documents.filter(d => d.access_scope === accessScope)
                console.log(`  → Found ${filtered.length} documents with ${accessScope} scope`)

                foldersWithDocuments.push({
                    ...folder,
                    documents: filtered,
                })
            } catch (err) {
                console.warn(`⚠️ Failed to fetch documents for folder ${folder.id}:`, err)
                foldersWithDocuments.push({
                    ...folder,
                    documents: [],
                })
            }
        }

        // Fetch unfoldered documents
        let unfoldered_documents: FolderDocumentResponse[] = []
        try {
            console.log(`\n📄 Fetching unfoldered documents...`)
            const allDocs = await fetchAllPages(
                (params) => fetchAllDocuments({ ...params, access_scope: accessScope }),
                { page: 1 },
                `Unfoldered docs (${accessScope})`
            )

            unfoldered_documents = allDocs.filter(
                doc => !doc.folder || doc.folder.trim() === ''
            )
            console.log(`  → Found ${unfoldered_documents.length} unfoldered documents`)
        } catch (err) {
            console.warn('⚠️ Failed to fetch unfoldered documents:', err)
        }

        console.log('\n✅ [COMPLETE] Personal Documents Organized:', {
            folders: foldersWithDocuments.length,
            totalDocuments: foldersWithDocuments.reduce((sum, f) => sum + f.documents.length, 0),
            unfolderedDocuments: unfoldered_documents.length,
        })

        return {
            folders: foldersWithDocuments,
            unfoldered_documents,
        }
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch personal folders and documents'
        console.error('❌ Error fetching organized personal documents:', err)
        if (err instanceof ApiError) {
            throw err
        }
        throw new Error(message)
    }
}
