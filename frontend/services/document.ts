// services/document.ts - Document API service
import { api } from './api'
import type { Document, ApiResponse } from '@/types'

export const documentService = {
    async listDocuments(limit = 20, offset = 0): Promise<Document[]> {
        const data = await api.get<ApiResponse<Document[]>>(
            `/documents?limit=${limit}&offset=${offset}`
        )
        return data.data
    },

    async uploadDocument(file: File, folderId?: string): Promise<Document> {
        const formData = new FormData()
        formData.append('file', file)
        if (folderId) {
            formData.append('folder_id', folderId)
        }

        const response = await fetch(`${api.baseUrl}/documents/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
            },
            body: formData,
        })

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`)
        }

        const data = await response.json()
        return data.data
    },

    async deleteDocument(documentId: string): Promise<void> {
        await api.delete(`/documents/${documentId}`)
    },

    async getDocumentDetails(documentId: string): Promise<Document> {
        const data = await api.get<ApiResponse<Document>>(`/documents/${documentId}`)
        return data.data
    },
}
