'use client'

import { useState, useCallback, useEffect } from 'react'
import { ChatService, MessageDTO, ConversationDTO } from '@/services/chatService'
import { useToast } from './useToast'
import { Message } from '@/components/features/chat/ChatMessages'

interface UseChatOptions {
    autoFetchConversations?: boolean
    onConversationCreated?: (conversation: ConversationDTO) => void
    onMessageSent?: (message: MessageDTO) => void
}

export const useChat = (options: UseChatOptions = {}) => {
    const { autoFetchConversations = true, onConversationCreated, onMessageSent } = options
    const { showError, showSuccess } = useToast()

    // State
    const [conversations, setConversations] = useState<ConversationDTO[]>([])
    const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
    const [messages, setMessages] = useState<Message[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [isFetchingConversations, setIsFetchingConversations] = useState(false)

    // Check if we have authentication token
    const hasToken = typeof window !== 'undefined' && !!localStorage.getItem('auth_token')  // Fixed: access_token -> auth_token

    // Fetch conversations
    const fetchConversations = useCallback(async (search?: string) => {
        try {
            setIsFetchingConversations(true)
            console.log('🔄 Fetching conversations...', { search, hasToken })
            const result = await ChatService.getConversations(1, 50, search)
            console.log('✅ Conversations fetched:', {
                count: result.data?.length || 0,
                total: result.total,
                data: result.data
            })
            setConversations(result.data)
        } catch (error) {
            showError('Không thể tải danh sách cuộc trò chuyện')
            console.error('❌ Failed to fetch conversations:', error)
            console.error('Error details:', {
                status: (error as any)?.response?.status,
                data: (error as any)?.response?.data
            })
        } finally {
            setIsFetchingConversations(false)
        }
    }, [showError, hasToken])

    // Fetch messages for a conversation
    const fetchMessages = useCallback(async (conversationId: string) => {
        try {
            setIsLoading(true)
            const result = await ChatService.getMessages(conversationId)
            const formattedMessages: Message[] = result.data.map((msg: MessageDTO) => ({
                id: msg.id,
                role: msg.role,
                content: msg.content,
                citations: msg.citations,
                timestamp: new Date(msg.created_at),
            }))
            setMessages(formattedMessages)
        } catch (error) {
            showError('Không thể tải tin nhắn')
            console.error('Failed to fetch messages:', error)
        } finally {
            setIsLoading(false)
        }
    }, [showError])

    // Create new conversation
    const createConversation = useCallback(async (title?: string) => {
        try {
            setIsLoading(true)
            const conversation = await ChatService.createConversation(title)
            setConversations((prev) => [conversation, ...prev])
            setCurrentConversationId(conversation.id)
            setMessages([])
            onConversationCreated?.(conversation)
            showSuccess('Tạo cuộc trò chuyện mới thành công')
            return conversation
        } catch (error) {
            showError('Không thể tạo cuộc trò chuyện mới')
            console.error('Failed to create conversation:', error)
            return null
        } finally {
            setIsLoading(false)
        }
    }, [showError, showSuccess, onConversationCreated])

    // Send message (Streaming support)
    const sendMessage = useCallback(
        async (content: string, attachments?: File[]) => {
            if (!content.trim()) return

            try {
                setIsLoading(true)

                // 1. Quản lý Conversation
                let convId = currentConversationId
                if (!convId) {
                    const conv = await createConversation(content.substring(0, 50))
                    if (!conv) return
                    convId = conv.id
                }

                // 2. Thêm tin nhắn User lạc quan
                const userMsg: Message = {
                    id: `user-${Date.now()}`,
                    role: 'user',
                    content,
                    timestamp: new Date(),
                }
                setMessages((prev) => [...prev, userMsg])

                // 3. Thêm tin nhắn Bot trống để nhận stream
                const botMsgId = `bot-${Date.now()}`
                const initialBotMsg: Message = {
                    id: botMsgId,
                    role: 'assistant',
                    content: '',
                    timestamp: new Date(),
                }
                setMessages((prev) => [...prev, initialBotMsg])

                // 4. Gọi Stream API
                let fullContent = ''
                await ChatService.sendMessageStream(content, convId, (chunk) => {
                    fullContent += chunk
                    setMessages((prev) => 
                        prev.map(msg => msg.id === botMsgId ? { ...msg, content: fullContent } : msg)
                    )
                })

                // 5. Cập nhật danh sách hội thoại nếu cần
                fetchConversations()

            } catch (error) {
                showError('Lỗi kết nối máy chủ. Vui lòng thử lại.')
                console.error('Streaming error:', error)
            } finally {
                setIsLoading(false)
            }
        },
        [currentConversationId, createConversation, fetchConversations, showError]
    )

    // Provide feedback
    const sendFeedback = useCallback(async (messageId: string, isHelpful: boolean) => {
        try {
            await ChatService.sendFeedback(messageId, isHelpful)
            showSuccess(isHelpful ? 'Cảm ơn phản hồi của bạn!' : 'Cảm ơn phản hồi của bạn!')
        } catch (error) {
            showError('Không thể gửi phản hồi')
            console.error('Failed to send feedback:', error)
        }
    }, [showError, showSuccess])

    // Select conversation
    const selectConversation = useCallback(
        (conversationId: string) => {
            setCurrentConversationId(conversationId)
            fetchMessages(conversationId)
        },
        [fetchMessages]
    )

    // Initialize - fetch conversations on mount when authenticated
    useEffect(() => {
        if (autoFetchConversations && hasToken) {
            fetchConversations()
        }
    }, [autoFetchConversations, fetchConversations, hasToken])

    return {
        // State
        conversations,
        currentConversationId,
        messages,
        isLoading,
        isFetchingConversations,

        // Actions
        createConversation,
        sendMessage,
        sendFeedback,
        selectConversation,
        fetchConversations,
        fetchMessages,
        setCurrentConversationId,
    }
}
