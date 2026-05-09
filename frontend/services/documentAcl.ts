/**
 * Document & Folder ACL Service
 *
 * Normalizes backend permission endpoints for the documents dashboard.
 */

import { api } from '@/services/api'

export type PermissionSubjectType = 'account' | 'role'
export type PermissionLevel = 'read' | 'write' | 'delete'

export interface PermissionItem {
    id: string
    subject_type: PermissionSubjectType
    subject_id: string
    subject_name: string | null
    permission: PermissionLevel
    is_active?: boolean
    created_at?: string | null
    updated_at?: string | null
    precedence?: string | null
    folder_id?: string | null
    document_id?: string | null
}

export interface FolderPermissionsResponse {
    folder_id: string
    folder_name: string
    access_scope: string
    permissions: PermissionItem[]
    total_permissions: number
}

export interface DocumentPermissionsResponse {
    document_id: string
    permissions: PermissionItem[]
}

export interface FolderPermissionsListEntry {
    folder_id: string
    folder_name: string
    access_scope: string
    permissions: PermissionItem[]
    total_permissions: number
}

export interface DocumentPermissionsListEntry {
    document_id: string
    document_name: string
    access_scope: string
    permissions: PermissionItem[]
    total_permissions: number
}

export interface PaginatedPermissionListResponse<T> {
    items: T[]
    pagination: {
        page: number
        page_size: number
        total_items: number
        total_pages: number
        has_next: boolean
        has_prev: boolean
    }
}

export interface PermissionGrantPayload {
    subject_type: PermissionSubjectType
    subject_id: string
    permission: PermissionLevel
    precedence?: 'inherit' | 'override' | 'deny'
}

function unwrapEnvelope<T>(response: any): T {
    if (response?.data?.permissions && response?.data?.folder_id) {
        return response.data as T
    }

    if (Array.isArray(response?.data)) {
        return response.data as T
    }

    if (response?.data && typeof response.data === 'object' && 'data' in response.data) {
        return response.data.data as T
    }

    if (response?.data) {
        return response.data as T
    }

    return response as T
}

function ensureSuccess(response: any, fallbackMessage: string) {
    if (response && typeof response === 'object' && 'success' in response && response.success === false) {
        throw new Error(response.message || fallbackMessage)
    }
}

function buildQueryString(params: Record<string, string | number | undefined>): string {
    const query = new URLSearchParams()

    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            query.set(key, String(value))
        }
    })

    const queryString = query.toString()
    return queryString ? `?${queryString}` : ''
}

function unwrapPaginatedEnvelope<T>(response: any): PaginatedPermissionListResponse<T> {
    const payload = response?.data?.data || response?.data || response

    if (payload && typeof payload === 'object' && 'items' in payload && 'pagination' in payload) {
        return payload as PaginatedPermissionListResponse<T>
    }

    return {
        items: [],
        pagination: {
            page: 1,
            page_size: 20,
            total_items: 0,
            total_pages: 0,
            has_next: false,
            has_prev: false,
        },
    }
}

export async function fetchFolderPermissions(folderId: string, grantedById?: string): Promise<FolderPermissionsResponse> {
    try {
        const response = await api.get<any>(`/folders/${folderId}/permissions${buildQueryString({ granted_by_id: grantedById || undefined })}`)
        ensureSuccess(response, 'Failed to fetch folder permissions')
        return unwrapEnvelope<FolderPermissionsResponse>(response)
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to fetch folder permissions'
        throw new Error(message)
    }
}

export async function fetchDocumentPermissions(documentId: string, grantedById?: string): Promise<DocumentPermissionsResponse> {
    try {
        const response = await api.get<any>(`/documents/${documentId}/permissions${buildQueryString({ granted_by_id: grantedById || undefined })}`)
        ensureSuccess(response, 'Failed to fetch document permissions')

        const permissions = unwrapEnvelope<PermissionItem[]>(response)
        return {
            document_id: documentId,
            permissions: Array.isArray(permissions) ? permissions : [],
        }
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to fetch document permissions'
        throw new Error(message)
    }
}

export async function fetchAllFolderPermissions(page = 1, pageSize = 20, search = '', grantedById?: string): Promise<PaginatedPermissionListResponse<FolderPermissionsListEntry>> {
    try {
        const response = await api.get<any>(`/folders/permissions${buildQueryString({
            page,
            page_size: pageSize,
            search: search || undefined,
            granted_by_id: grantedById || undefined,
        })}`)
        ensureSuccess(response, 'Failed to fetch folder permissions overview')
        return unwrapPaginatedEnvelope<FolderPermissionsListEntry>(response)
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to fetch folder permissions overview'
        throw new Error(message)
    }
}

export async function fetchAllDocumentPermissions(page = 1, pageSize = 20, search = '', grantedById?: string): Promise<PaginatedPermissionListResponse<DocumentPermissionsListEntry>> {
    try {
        const response = await api.get<any>(`/documents/permissions${buildQueryString({
            page,
            page_size: pageSize,
            search: search || undefined,
            granted_by_id: grantedById || undefined,
        })}`)
        ensureSuccess(response, 'Failed to fetch document permissions overview')
        return unwrapPaginatedEnvelope<DocumentPermissionsListEntry>(response)
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to fetch document permissions overview'
        throw new Error(message)
    }
}

export async function grantFolderPermission(folderId: string, payload: PermissionGrantPayload): Promise<PermissionItem> {
    try {
        const response = await api.post<any>(`/folders/${folderId}/permissions`, payload)
        ensureSuccess(response, 'Failed to grant folder permission')
        return unwrapEnvelope<PermissionItem>(response)
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to grant folder permission'
        throw new Error(message)
    }
}

export async function grantDocumentPermission(documentId: string, payload: PermissionGrantPayload): Promise<PermissionItem> {
    try {
        const response = await api.post<any>(`/documents/${documentId}/permissions`, payload)
        ensureSuccess(response, 'Failed to grant document permission')
        return unwrapEnvelope<PermissionItem>(response)
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to grant document permission'
        throw new Error(message)
    }
}

export async function revokeFolderPermission(
    folderId: string,
    subjectType: PermissionSubjectType,
    subjectId: string,
    permission: PermissionLevel
): Promise<void> {
    try {
        await api.delete(`/folders/${folderId}/permissions/${subjectType}/${subjectId}/${permission}`)
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to revoke folder permission'
        throw new Error(message)
    }
}

export async function revokeDocumentPermission(
    documentId: string,
    subjectType: PermissionSubjectType,
    subjectId: string,
    permission: PermissionLevel
): Promise<void> {
    try {
        await api.delete(`/documents/${documentId}/permissions/${subjectType}/${subjectId}/${permission}`)
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to revoke document permission'
        throw new Error(message)
    }
}