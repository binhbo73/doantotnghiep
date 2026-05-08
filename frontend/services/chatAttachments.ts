/**
 * Chat Attachments Service
 * Fetch available documents/folders for attaching to conversations
 * 
 * API: GET /api/v1/chat/available-attachments
 * Returns only documents/folders that user has access to based on:
 * - access_scope (personal/department/company)
 * - User roles
 * - DocumentPermission entries
 * - FolderPermission entries
 */

import { api, ApiError } from './api'
import { FolderDocumentResponse, FolderResponse } from './folder'

export interface AvailableAttachmentsResponse {
    documents: FolderDocumentResponse[]
    folders: FolderResponse[]
    pagination?: {
        total_documents: number
        total_folders: number
    }
}

/**
 * Fetch all available documents and folders for chat attachment
 * 
 * Filters based on:
 * - User's access_scope permissions
 * - User's role permissions  
 * - Explicit DocumentPermission entries
 * - Explicit FolderPermission entries
 * 
 * GET /api/v1/chat/available-attachments
 */
export async function fetchAvailableAttachments(): Promise<AvailableAttachmentsResponse> {
    try {
        const response = await api.get<any>('/chat/available-attachments')

        console.log('📎 Available Attachments Response:', JSON.stringify(response, null, 2).substring(0, 800))

        // ResponseBuilder wraps response in { data: {...} }
        let data = response.data || response

        return {
            documents: data.documents || [],
            folders: data.folders || [],
            pagination: data.pagination
        }
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch available attachments'
        console.error('❌ Error fetching available attachments:', err)
        if (err instanceof ApiError) {
            throw err
        }
        throw new Error(message)
    }
}
