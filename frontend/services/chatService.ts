import { apiClient } from '@/lib/api-client'
import { API_ENDPOINTS } from '@/config/api-endpoints'
import { buildApiUrl } from '@/config/api'

export interface ConversationDTO {
    id: string
    title: string
    description?: string
    created_at: string
    updated_at: string
    attached_documents?: ConversationAttachedDocumentDTO[]
    attached_folders?: ConversationAttachedFolderDTO[]
}

export interface ConversationAttachedDocumentDTO {
    id: string
    name: string
    file_type?: string
    folder_id?: string | null
}

export interface ConversationAttachedFolderDTO {
    id: string
    name: string
}

export interface ConversationAttachmentsDTO {
    conversation_id: string
    attached_documents: ConversationAttachedDocumentDTO[]
    attached_folders: ConversationAttachedFolderDTO[]
}

export interface MessageDTO {
    id: string
    conversation_id: string
    role: 'user' | 'assistant'
    content: string
    citations?: CitationDTO[]
    created_at: string
}

export interface CitationDTO {
    id: string
    number?: number | string
    title: string
    source_label?: string
    description?: string
    answer_context?: string
    excerpt?: string
    page?: string | number
    chunk_index?: number
    line_start?: number
    line_end?: number
    start_char?: number
    end_char?: number
    document_id?: string
    chunk_id?: string
    source?: string
    score?: number
    url?: string
    type?: string
    asset_id?: string
    asset_caption?: string
    asset_image_path?: string
    asset_page_number?: number | string
    asset_sheet_name?: string
    asset_anchor_cell?: string
    asset_paragraph_index?: number | null
    asset_position_in_document?: Record<string, number> | null
    asset_context_text?: string
    asset?: {
        id: string
        image_url?: string | null
        thumbnail_url?: string | null
        caption?: string | null
        page_number?: number | null
        sheet_name?: string | null
        anchor_cell?: string | null
        paragraph_index?: number | null
        position_in_document?: Record<string, number> | null
        context_text?: string | null
    }
}

export interface SendMessageRequest {
    content: string
    conversation_id?: string
    attachments?: File[]
}

export interface ConversationAttachmentPayload {
    documentIds?: string[]
    folderIds?: string[]
}

export interface SendMessageResponse {
    message?: MessageDTO
    id?: string
    conversation_id: string
    role?: 'user' | 'assistant'
    content?: string
    citations?: CitationDTO[]
    created_at?: string
}

export class ChatService {
    /**
     * Get all conversations for the current user
     */
    static async getConversations(page: number = 1, pageSize: number = 50, search?: string) {
        try {
            const params = new URLSearchParams({
                page: page.toString(),
                page_size: pageSize.toString(),
            })

            if (search) {
                params.append('search', search)
            }

            console.log('📤 Calling API:', `${API_ENDPOINTS.CHAT.CONVERSATIONS}/?${params.toString()}`)
            const response = await apiClient.get(
                `${API_ENDPOINTS.CHAT.CONVERSATIONS}/?${params.toString()}`
            )

            console.log('📥 Full API response:', response.data)

            // Handle paginated response format from backend
            const { items = [], pagination = {} } = response.data.data || {}
            console.log('📊 Parsed response:', {
                itemsCount: items.length,
                items,
                pagination
            })

            return {
                data: items,
                total: pagination.total_items || 0,
                page: pagination.page || page,
                pageSize: pagination.page_size || pageSize,
                totalPages: pagination.total_pages || 0,
            }
        } catch (error) {
            console.error('❌ Failed to fetch conversations:', error)
            console.error('Error response:', (error as any)?.response?.data)
            throw error
        }
    }

    /**
     * Get a specific conversation
     */
    static async getConversation(conversationId: string): Promise<ConversationDTO> {
        try {
            const response = await apiClient.get(
                `${API_ENDPOINTS.CHAT.CONVERSATIONS}/${conversationId}/`
            )
            return response.data.data
        } catch (error) {
            console.error(`Failed to fetch conversation ${conversationId}:`, error)
            throw error
        }
    }

    /**
     * Get documents/folders attached to a conversation
     */
    static async getConversationAttachments(conversationId: string): Promise<ConversationAttachmentsDTO> {
        try {
            const response = await apiClient.get(
                `${API_ENDPOINTS.CHAT.CONVERSATIONS}/${conversationId}/attachments/`
            )
            return response.data.data
        } catch (error) {
            console.error(`Failed to fetch conversation attachments ${conversationId}:`, error)
            throw error
        }
    }

    /**
     * Create a new conversation
     */
    static async createConversation(title?: string): Promise<ConversationDTO> {
        try {
            const response = await apiClient.post(API_ENDPOINTS.CHAT.CONVERSATIONS, {
                title: title || 'Cuộc trò chuyện mới',
            })
            return response.data.data
        } catch (error) {
            console.error('Failed to create conversation:', error)
            throw error
        }
    }

    /**
     * Attach existing system documents/folders to a conversation
     */
    static async attachConversationResources(
        conversationId: string,
        payload: ConversationAttachmentPayload
    ): Promise<ConversationDTO> {
        try {
            const response = await apiClient.post(
                `${API_ENDPOINTS.CHAT.CONVERSATIONS}/${conversationId}/attachments/`,
                {
                    document_ids: payload.documentIds || [],
                    folder_ids: payload.folderIds || [],
                }
            )

            return response.data.data
        } catch (error) {
            console.error(`Failed to attach resources for conversation ${conversationId}:`, error)
            throw error
        }
    }

    /**
     * Get messages in a conversation
     */
    static async getMessages(conversationId: string, page: number = 1, pageSize: number = 50) {
        try {
            const params = new URLSearchParams({
                page: page.toString(),
                page_size: pageSize.toString(),
            })

            const response = await apiClient.get(
                `${API_ENDPOINTS.CHAT.CONVERSATIONS}/${conversationId}/messages/?${params.toString()}`
            )

            // Handle paginated response format from backend
            const { items = [], pagination = {} } = response.data.data || {}
            return {
                data: items,
                total: pagination.total_items || 0,
                page: pagination.page || page,
                pageSize: pagination.page_size || pageSize,
            }
        } catch (error) {
            console.error(`Failed to fetch messages for conversation ${conversationId}:`, error)
            throw error
        }
    }

    /**
     * Send a message with STREAMING support.
     *
     * @param content        - Nội dung câu hỏi
     * @param onChunk        - Callback nhận từng text chunk khi stream
     * @param conversationId - ID cuộc trò chuyện (optional)
     * @param documentIds    - IDs tài liệu đính kèm để giới hạn phạm vi RAG search
     * @param folderIds      - IDs thư mục đính kèm để giới hạn phạm vi RAG search
     */
    static async sendMessageStream(
        content: string,
        onChunk: (text: string) => void,
        conversationId?: string,
        documentIds?: string[],
        folderIds?: string[],
        onStatus?: (status: string) => void,
        onCitations?: (citations: any[]) => void
    ): Promise<void> {
        try {
            const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null

            // ⚠️ QUAN TRỌNG: Không dùng Next.js rewrite (/api/v1/...) cho streaming.
            // Next.js rewrites() buffer toàn bộ response trước khi forward → phá hủy SSE.
            // Gọi thẳng backend URL để nhận stream real-time.
            const backendBase = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') || 'http://localhost:8000/api/v1'
            const streamUrl = `${backendBase}/${API_ENDPOINTS.CHAT.MESSAGES}/stream/`

            const response = await fetch(streamUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    content,
                    conversation_id: conversationId,
                    // Truyền IDs tài liệu/thư mục để backend giới hạn phạm vi RAG search.
                    // Backend sẽ ưu tiên danh sách này; nếu rỗng thì đọc từ ConversationAttachedDocument.
                    ...(documentIds?.length ? { document_ids: documentIds } : {}),
                    ...(folderIds?.length ? { folder_ids: folderIds } : {}),
                })
            })

            if (!response.ok) {
                const errText = await response.text().catch(() => '')
                throw new Error(`Stream request failed: ${response.status} ${errText.substring(0, 200)}`)
            }

            const reader = response.body?.getReader()
            const decoder = new TextDecoder()
            let bufferedText = ''

            if (!reader) return

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                bufferedText += decoder.decode(value, { stream: true })
                const lines = bufferedText.split(/\r?\n/)
                bufferedText = lines.pop() || ''

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const payload = line.slice(6).trim()
                        if (!payload) continue
                        try {
                            const data = JSON.parse(payload)
                            if (data.status && onStatus) onStatus(data.status)
                            if (data.text) onChunk(data.text)
                            if (data.citations && onCitations) onCitations(data.citations)
                            if (data.error) throw new Error(data.error)
                        } catch (e) {
                            console.error('Error parsing stream line:', e)
                        }
                    }
                }
            }

            bufferedText += decoder.decode()
            const tailLines = bufferedText.split(/\r?\n/)
            for (const line of tailLines) {
                if (!line.startsWith('data: ')) continue
                const payload = line.slice(6).trim()
                if (!payload) continue
                try {
                    const data = JSON.parse(payload)
                    if (data.status && onStatus) onStatus(data.status)
                    if (data.text) onChunk(data.text)
                    if (data.citations && onCitations) onCitations(data.citations)
                    if (data.error) throw new Error(data.error)
                } catch (e) {
                    console.error('Error parsing stream line:', e)
                }
            }
        } catch (error) {
            console.error('Streaming failed:', error)
            throw error
        }
    }

    /**
     * Send a message (triggers RAG pipeline)
     */
    static async sendMessage(
        content: string,
        conversationId?: string,
        attachments?: File[]
    ): Promise<SendMessageResponse> {
        try {
            const formData = new FormData()
            formData.append('content', content)

            if (conversationId) {
                formData.append('conversation_id', conversationId)
            }

            // Add attachments if provided
            if (attachments && attachments.length > 0) {
                attachments.forEach((file, index) => {
                    formData.append(`attachments`, file)
                })
            }

            const response = await apiClient.post(`${API_ENDPOINTS.CHAT.MESSAGES}/`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            })

            return response.data.data
        } catch (error) {
            console.error('Failed to send message:', error)
            throw error
        }
    }

    /**
     * Provide feedback on a message
     */
    static async sendFeedback(messageId: string, rating: string, comment?: string) {
        // Prevent sending feedback for temporary optimistic IDs
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
        if (!uuidRegex.test(messageId)) {
            const err = new Error(`Message ${messageId} is not a valid server ID`)
            console.error(err)
            throw err
        }

        try {
            const response = await apiClient.post(
                `${API_ENDPOINTS.CHAT.MESSAGES}/${messageId}/feedback/`,
                {
                    rating,
                    comment,
                }
            )
            return response.data.data
        } catch (error) {
            console.error(`Failed to send feedback for message ${messageId}:`, error)
            throw error
        }
    }

    /**
     * Delete a conversation
     */
    static async deleteConversation(conversationId: string) {
        try {
            const response = await apiClient.delete(
                `${API_ENDPOINTS.CHAT.CONVERSATIONS}/${conversationId}/`
            )
            return response.data
        } catch (error) {
            console.error(`Failed to delete conversation ${conversationId}:`, error)
            throw error
        }
    }

    /**
     * Update conversation title
     */
    static async updateConversation(conversationId: string, title: string) {
        try {
            const response = await apiClient.patch(
                `${API_ENDPOINTS.CHAT.CONVERSATIONS}/${conversationId}/`,
                {
                    title,
                }
            )
            return response.data.data
        } catch (error) {
            console.error(`Failed to update conversation ${conversationId}:`, error)
            throw error
        }
    }
}
