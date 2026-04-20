// services/chat.ts - Chat API service
import { api } from '@/services/api/client'
import type { Message, ApiResponse } from '@/types'

export const chatService = {
    async getMessages(conversationId: string, limit = 50, offset = 0): Promise<Message[]> {
        const data = await api.get<ApiResponse<Message[]>>(
            `/chat/messages?conversation_id=${conversationId}&limit=${limit}&offset=${offset}`
        )
        return data.data
    },

    async sendMessage(conversationId: string, content: string): Promise<Message> {
        const data = await api.post<ApiResponse<Message>>('/chat/send', {
            conversation_id: conversationId,
            content,
        })
        return data.data
    },

    async createConversation(title?: string): Promise<{ id: string; title: string }> {
        const data = await api.post<ApiResponse<{ id: string; title: string }>>('/chat/conversations', {
            title,
        })
        return data.data
    },
}
