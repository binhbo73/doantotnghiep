/**
 * API Type Definitions - Based on Backend Django Models
 * Uses Zod for runtime validation and type inference
 */

import { z } from 'zod'

// ============================================
// BASE SCHEMAS - Shared fields
// ============================================

const UUIDSchema = z.string().uuid()
const DateTimeSchema = z.string().datetime()

const BaseEntitySchema = z.object({
    is_deleted: z.boolean(),
    deleted_at: z.string().nullable(),
    created_at: DateTimeSchema,
    updated_at: DateTimeSchema,
})

// ============================================
// ACCOUNT / USER SCHEMAS
// ============================================

export const AccountStatusEnum = z.enum(['active', 'blocked', 'inactive'])
export type AccountStatus = z.infer<typeof AccountStatusEnum>

export const AccountSchema = z.object({
    id: UUIDSchema,
    username: z.string(),
    email: z.string().email(),
    first_name: z.string(),
    last_name: z.string(),
    status: AccountStatusEnum,
    last_login_at: z.string().datetime().nullable(),
    is_deleted: z.boolean(),
    deleted_at: z.string().datetime().nullable(),
    created_at: DateTimeSchema,
    updated_at: DateTimeSchema,
})
export type Account = z.infer<typeof AccountSchema>

// ============================================
// DEPARTMENT SCHEMAS
// ============================================

export const DepartmentSchema = z.object({
    id: UUIDSchema,
    name: z.string(),
    parent_id: UUIDSchema.nullable(),
    manager_id: UUIDSchema.nullable(),
    description: z.string().nullable(),
    is_deleted: z.boolean(),
    deleted_at: z.string().datetime().nullable(),
    created_at: DateTimeSchema,
    updated_at: DateTimeSchema,
})
export type Department = z.infer<typeof DepartmentSchema>

// ============================================
// DOCUMENT SCHEMAS
// ============================================

export const AccessScopeEnum = z.enum(['personal', 'department', 'company'])
export type AccessScope = z.infer<typeof AccessScopeEnum>

export const DocumentStatusEnum = z.enum(['pending', 'processing', 'completed', 'failed'])
export type DocumentStatus = z.infer<typeof DocumentStatusEnum>

export const DocumentSchema = z.object({
    id: UUIDSchema,
    filename: z.string(),
    original_name: z.string(),
    storage_path: z.string(),
    file_type: z.string(), // 'pdf', 'docx', 'txt', 'markdown'
    file_size: z.number().int().nonnegative(),
    mime_type: z.string().nullable(),
    uploader_id: UUIDSchema,
    department_id: UUIDSchema.nullable(),
    folder_id: UUIDSchema.nullable(),
    access_scope: AccessScopeEnum,
    is_public: z.boolean(),
    doc_language: z.string(), // 'vi', 'en'
    metadata: z.record(z.unknown()).default({}),
    version: z.number().int().positive(),
    embedding_model: z.string(),
    chunking_strategy: z.string(),
    s3_url: z.string().url().nullable(),
    status: DocumentStatusEnum,
    version_lock: z.number().int().nonnegative(),
    has_hierarchical_chunks: z.boolean(),
    is_deleted: z.boolean(),
    deleted_at: z.string().datetime().nullable(),
    created_at: DateTimeSchema,
    updated_at: DateTimeSchema,
})
export type Document = z.infer<typeof DocumentSchema>

export const DocumentDetailSchema = DocumentSchema.extend({
    uploader: AccountSchema.optional(),
    department: DepartmentSchema.optional(),
    folder: z.object({
        id: UUIDSchema,
        name: z.string(),
    }).optional(),
    tags: z.array(
        z.object({
            id: UUIDSchema,
            name: z.string(),
            color: z.string(),
        })
    ).default([]),
})
export type DocumentDetail = z.infer<typeof DocumentDetailSchema>

// ============================================
// FOLDER SCHEMAS
// ============================================

export const FolderSchema = z.object({
    id: UUIDSchema,
    name: z.string(),
    parent_id: UUIDSchema.nullable(),
    department_id: UUIDSchema.nullable(),
    access_scope: AccessScopeEnum,
    description: z.string().nullable(),
    metadata: z.record(z.unknown()).default({}),
    created_by_id: UUIDSchema.nullable(),
    is_deleted: z.boolean(),
    deleted_at: z.string().datetime().nullable(),
    created_at: DateTimeSchema,
    updated_at: DateTimeSchema,
})
export type Folder = z.infer<typeof FolderSchema>

export const FolderDetailSchema = FolderSchema.extend({
    created_by: AccountSchema.optional(),
    parent: FolderSchema.optional(),
})
export type FolderDetail = z.infer<typeof FolderDetailSchema>

// ============================================
// TAG SCHEMAS
// ============================================

export const TagSchema = z.object({
    id: UUIDSchema,
    name: z.string(),
    color: z.string(),
    description: z.string().nullable(),
    created_by_id: UUIDSchema.nullable(),
    is_deleted: z.boolean(),
    deleted_at: z.string().datetime().nullable(),
    created_at: DateTimeSchema,
    updated_at: DateTimeSchema,
})
export type Tag = z.infer<typeof TagSchema>

// ============================================
// CONVERSATION & MESSAGE SCHEMAS
// ============================================

export const ConversationSchema = z.object({
    id: UUIDSchema,
    account_id: UUIDSchema,
    title: z.string(),
    summary: z.string().nullable(),
    is_deleted: z.boolean(),
    deleted_at: z.string().datetime().nullable(),
    created_at: DateTimeSchema,
    updated_at: DateTimeSchema,
})
export type Conversation = z.infer<typeof ConversationSchema>

export const MessageRoleEnum = z.enum(['user', 'assistant', 'system'])
export type MessageRole = z.infer<typeof MessageRoleEnum>

export const CitationSchema = z.object({
    chunk_id: UUIDSchema.optional(),
    document_id: UUIDSchema.optional(),
    text: z.string().optional(),
    score: z.number().optional(),
})

export const MessageSchema = z.object({
    id: UUIDSchema,
    conversation_id: UUIDSchema,
    role: MessageRoleEnum,
    content: z.string(),
    citations: z.array(CitationSchema).default([]),
    tokens_used: z.number().int().nonnegative(),
    is_deleted: z.boolean(),
    deleted_at: z.string().datetime().nullable(),
    created_at: DateTimeSchema,
    updated_at: DateTimeSchema,
})
export type Message = z.infer<typeof MessageSchema>

// ============================================
// REQUEST SCHEMAS - What we send to API
// ============================================

export const ListDocumentsRequestSchema = z.object({
    limit: z.number().int().positive().default(20),
    offset: z.number().int().nonnegative().default(0),
    folder_id: UUIDSchema.optional(),
    status: DocumentStatusEnum.optional(),
    file_type: z.string().optional(),
    search: z.string().optional(),
})
export type ListDocumentsRequest = z.infer<typeof ListDocumentsRequestSchema>

export const UploadDocumentRequestSchema = z.object({
    file: z.instanceof(File),
    folder_id: UUIDSchema.optional(),
    access_scope: AccessScopeEnum.default('company'),
    doc_language: z.string().default('vi'),
    tags: z.array(UUIDSchema).default([]),
    metadata: z.record(z.unknown()).default({}),
})
export type UploadDocumentRequest = z.infer<typeof UploadDocumentRequestSchema>

export const DeleteDocumentRequestSchema = z.object({
    document_id: UUIDSchema,
    hard_delete: z.boolean().default(false),
})
export type DeleteDocumentRequest = z.infer<typeof DeleteDocumentRequestSchema>

export const ListFoldersRequestSchema = z.object({
    limit: z.number().int().positive().default(20),
    offset: z.number().int().nonnegative().default(0),
    parent_id: UUIDSchema.optional(),
    department_id: UUIDSchema.optional(),
})
export type ListFoldersRequest = z.infer<typeof ListFoldersRequestSchema>

export const CreateFolderRequestSchema = z.object({
    name: z.string().min(1).max(100),
    parent_id: UUIDSchema.optional(),
    department_id: UUIDSchema.optional(),
    access_scope: AccessScopeEnum.default('company'),
    description: z.string().max(1000).optional(),
})
export type CreateFolderRequest = z.infer<typeof CreateFolderRequestSchema>

export const SendMessageRequestSchema = z.object({
    conversation_id: UUIDSchema,
    content: z.string().min(1).max(10000),
    document_ids: z.array(UUIDSchema).default([]),
    folder_ids: z.array(UUIDSchema).default([]),
})
export type SendMessageRequest = z.infer<typeof SendMessageRequestSchema>

export const ListMessagesRequestSchema = z.object({
    conversation_id: UUIDSchema,
    limit: z.number().int().positive().default(50),
    offset: z.number().int().nonnegative().default(0),
})
export type ListMessagesRequest = z.infer<typeof ListMessagesRequestSchema>

// ============================================
// RESPONSE SCHEMAS - What we get from API
// ============================================

export const PaginatedResponseSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
    z.object({
        items: z.array(itemSchema),
        total: z.number().int().nonnegative(),
        page: z.number().int().positive(),
        limit: z.number().int().positive(),
        pages: z.number().int().nonnegative(),
        has_next: z.boolean(),
        has_previous: z.boolean(),
    })

export const ApiResponseSchema = <T extends z.ZodTypeAny>(dataSchema: T) =>
    z.object({
        data: dataSchema,
        success: z.boolean(),
        message: z.string().optional(),
        error: z.string().optional(),
        timestamp: DateTimeSchema.optional(),
    })

export const ListDocumentsResponseSchema = PaginatedResponseSchema(DocumentSchema)
export type ListDocumentsResponse = z.infer<typeof ListDocumentsResponseSchema>

export const ListFoldersResponseSchema = PaginatedResponseSchema(FolderSchema)
export type ListFoldersResponse = z.infer<typeof ListFoldersResponseSchema>

export const ListMessagesResponseSchema = PaginatedResponseSchema(MessageSchema)
export type ListMessagesResponse = z.infer<typeof ListMessagesResponseSchema>

export const UploadDocumentResponseSchema = ApiResponseSchema(DocumentSchema)
export type UploadDocumentResponse = z.infer<typeof UploadDocumentResponseSchema>

export const CreateConversationResponseSchema = ApiResponseSchema(ConversationSchema)
export type CreateConversationResponse = z.infer<typeof CreateConversationResponseSchema>

export const SendMessageResponseSchema = ApiResponseSchema(MessageSchema)
export type SendMessageResponse = z.infer<typeof SendMessageResponseSchema>

// ============================================
// ERROR SCHEMAS
// ============================================

export const ApiErrorSchema = z.object({
    error: z.string(),
    message: z.string(),
    status: z.number().int(),
    details: z.unknown().optional(),
    timestamp: DateTimeSchema.optional(),
    request_id: z.string().optional(),
})
export type ApiError = z.infer<typeof ApiErrorSchema>

// ============================================
// AUTH SCHEMAS
// ============================================
// LOGIN/AUTH SCHEMAS
// ============================================

export const LoginRequestSchema = z.object({
    email: z.string().email(),
    password: z.string().min(1),
})
export type LoginRequest = z.infer<typeof LoginRequestSchema>

// Role object in JWT token
export const RoleSchema = z.object({
    id: UUIDSchema,
    code: z.string(),
    name: z.string(),
})
export type Role = z.infer<typeof RoleSchema>

// Login response data (inside the 'data' wrapper)
export const LoginDataSchema = z.object({
    user: AccountSchema,
    access_token: z.string(),
    refresh_token: z.string(),
    permissions: z.array(z.string()),
    roles: z.array(RoleSchema),
    department_id: UUIDSchema.nullable(),
})
export type LoginData = z.infer<typeof LoginDataSchema>

// Login response - wrapped response from backend with LoginData inside
export type LoginResponse = {
    success: boolean
    status_code: number
    message: string
    data: LoginData
    timestamp?: string
}

export const RegisterRequestSchema = z.object({
    email: z.string().email(),
    password: z.string().min(8),
    username: z.string().min(3).max(150),
    first_name: z.string(),
    last_name: z.string(),
})
export type RegisterRequest = z.infer<typeof RegisterRequestSchema>

// ============================================
// REQUEST/RESPONSE ENVELOPES
// ============================================

export type ApiResponseEnvelope<T> = {
    data?: T
    success: boolean
    message?: string
    error?: string
    timestamp?: string
}

export type PaginatedResponseEnvelope<T> = {
    items: T[]
    total: number
    page: number
    limit: number
    pages: number
    has_next: boolean
    has_previous: boolean
}
