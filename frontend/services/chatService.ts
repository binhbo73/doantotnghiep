import { apiClient } from '@/lib/api-client'
import { API_ENDPOINTS } from '@/config/api-endpoints'

export interface ConversationDTO {
    id: string
    title: string
    description?: string
    created_at: string
    updated_at: string
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
    title: string
    description?: string
    page?: string
    type?: 'pdf' | 'document' | 'article'
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
    static async getConversation(conversationId: string) {
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
     * Create a new conversation
     */
    static async createConversation(title?: string) {
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
    ) {
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
     * Send a message with STREAMING support
     */
    static async sendMessageStream(
        content: string,
        onChunk: (text: string) => void,
        conversationId?: string
    ): Promise<void> {
        try {
            const token = localStorage.getItem('auth_token')
            const response = await fetch(`${API_ENDPOINTS.CHAT.MESSAGES}/stream/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    content,
                    conversation_id: conversationId
                })
            })

            if (!response.ok) throw new Error('Stream request failed')

            const reader = response.body?.getReader()
            const decoder = new TextDecoder()

            if (!reader) return

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                const chunk = decoder.decode(value)
                const lines = chunk.split('\n')

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6))
                            if (data.text) onChunk(data.text)
                            if (data.error) throw new Error(data.error)
                        } catch (e) {
                            console.error('Error parsing stream line:', e)
                        }
                    }
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
