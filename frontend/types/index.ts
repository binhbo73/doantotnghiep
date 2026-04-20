// types/index.ts - TypeScript types/interfaces
export interface User {
    id: string
    email: string
    name: string
    role: 'admin' | 'user'
}

export interface Message {
    id: string
    content: string
    timestamp: string
    sender: User
    conversation_id: string
}

export interface Document {
    id: string
    name: string
    type: string
    size: number
    uploadedAt: string
    url?: string
}

export interface ApiResponse<T = unknown> {
    data: T
    message?: string
    success: boolean
    error?: string
}

export interface PaginatedResponse<T> {
    items: T[]
    total: number
    page: number
    limit: number
    pages: number
}

export interface Conversation {
    id: string
    title: string
    createdAt: string
    updatedAt: string
}
