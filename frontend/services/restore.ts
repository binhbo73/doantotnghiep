import { api } from '@/services/api/client'

export type DeletedResource =
    | 'accounts'
    | 'user_profiles'
    | 'password_reset_tokens'
    | 'departments'
    | 'roles'
    | 'permissions'
    | 'role_permissions'
    | 'account_roles'
    | 'companies'
    | 'folders'
    | 'tags'
    | 'documents'
    | 'document_chunks'
    | 'chunk_revision_links'
    | 'document_permissions'
    | 'folder_permissions'
    | 'document_embeddings'
    | 'document_assets'
    | 'conversations'
    | 'conversation_documents'
    | 'conversation_folders'
    | 'messages'
    | 'human_feedback'
    | 'audit_logs'
    | 'async_tasks'
    | 'user_document_caches'

export type DeletedRecord = {
    id: string
    type: string
    name: string
    deleted_at: string | null
    created_at?: string | null
}

export type DeletedRecordsPage = {
    items: DeletedRecord[]
    page: number
    page_size: number
    total_items: number
    total_pages: number
}

type ApiEnvelope<T> = {
    success?: boolean
    message?: string
    data?: T
}

export async function listDeletedRecords(
    resource: DeletedResource,
    page = 1,
    pageSize = 20
): Promise<DeletedRecordsPage> {
    const query = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
    })
    const response = await api.get<ApiEnvelope<DeletedRecordsPage>>(
        `/deleted/${resource}?${query.toString()}`
    )

    return response.data || {
        items: [],
        page,
        page_size: pageSize,
        total_items: 0,
        total_pages: 1,
    }
}

export async function restoreDeletedRecord(
    resource: DeletedResource,
    id: string
): Promise<void> {
    await api.post(`/deleted/${resource}/${id}/restore`)
}
