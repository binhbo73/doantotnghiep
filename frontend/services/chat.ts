// services/chat.ts - Chat API service
import { api } from '@/services/api/client'
import type { Message, ApiResponse } from '@/types'

export interface Feedback {
    id: string
    message_id: string
    account_id: number
    account_username: string
    message_role: 'user' | 'assistant' | 'system'
    rating: 'upvote' | 'downvote'
    comment?: string | null
    created_at: string
    updated_at: string
}

export interface FeedbackRequest {
    rating: 'upvote' | 'downvote'
    comment?: string
}

export interface FeedbackStats {
    total: number
    upvote_count: number
    downvote_count: number
}

export interface FeedbackListResponse {
    message_id: string
    stats: FeedbackStats
    feedbacks: Feedback[]
}

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

    // ============================================================
    // FEEDBACK METHODS
    // ============================================================

    /**
     * Submit or update feedback on a message
     * - Only works on assistant messages
     * - One feedback per user per message (update if exists)
     * - Soft-delete recovery: restores deleted feedback if resubmitting
     */
    async submitFeedback(messageId: string, feedback: FeedbackRequest): Promise<Feedback> {
        const data = await api.post<ApiResponse<Feedback>>(
            `/chat/messages/${messageId}/feedback`,
            feedback
        )
        return data.data
    },

    /**
     * Get all feedback on a message (with stats)
     * - Returns feedback count and breakdown (upvote/downvote)
     * - Only shows non-deleted feedback
     * - Optional: filter by rating
     */
    async getFeedback(messageId: string, rating?: 'upvote' | 'downvote'): Promise<FeedbackListResponse> {
        let url = `/chat/messages/${messageId}/feedback`
        if (rating) {
            url += `?rating=${rating}`
        }
        const data = await api.get<ApiResponse<FeedbackListResponse>>(url)
        return data.data
    },

    /**
     * Delete own feedback on a message (soft delete)
     * - Can only delete feedback created by user
     * - Performs soft delete for audit trail
     */
    async deleteFeedback(messageId: string): Promise<void> {
        await api.delete(`/chat/messages/${messageId}/feedback`)
    },
}
