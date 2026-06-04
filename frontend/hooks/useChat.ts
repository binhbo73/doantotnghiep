'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { ChatService } from '@/services/chatService'
import type {
    MessageDTO,
    ConversationDTO,
    ConversationAttachmentPayload,
    ConversationAttachmentsDTO,
} from '@/services/chatService'
import { useToast } from './useToast'
import { getAuthToken } from '@/services/auth'
import { logger } from '@/services/logger'
import type { Message } from '@/components/features/chat/ChatMessages'
import type { ChatSelectedResourceItem } from '@/components/features/chat/ChatInput'

interface UseChatOptions {
    autoFetchConversations?: boolean
    canCreateConversations?: boolean
    onConversationCreated?: (conversation: ConversationDTO) => void
    onMessageSent?: (message: MessageDTO) => void
}

export interface ConversationAttachmentViewState {
    documents: ChatSelectedResourceItem[]
    folders: ChatSelectedResourceItem[]
}

const emptyConversationAttachments: ConversationAttachmentViewState = {
    documents: [],
    folders: [],
}

const mapConversationAttachments = (
    attachments?: Pick<ConversationDTO, 'attached_documents' | 'attached_folders'> | ConversationAttachmentsDTO | null
): ConversationAttachmentViewState => ({
    documents: (attachments?.attached_documents || []).map((doc) => ({
        id: doc.id,
        name: doc.name || 'Tai lieu khong xac dinh',
        detail: doc.file_type || 'document',
    })),
    folders: (attachments?.attached_folders || []).map((folder) => ({
        id: folder.id,
        name: folder.name || 'Thu muc khong xac dinh',
        detail: 'folder',
    })),
})

const normalizeCitationBundle = (raw: MessageDTO['citations'] | any): Pick<Message, 'citations' | 'grounding' | 'factAttribution'> => {
    const citations = Array.isArray(raw) ? raw : Array.isArray(raw?.citations) ? raw.citations : []

    if (!citations.length) {
        return { citations: [], grounding: undefined, factAttribution: [] }
    }

    let grounding: Message['grounding']
    let factAttribution: Message['factAttribution'] = []
    const realCitations: any[] = []

    citations.forEach((citation: any) => {
        if (citation?._grounding) {
            grounding = citation._grounding
            if (Array.isArray(citation._grounding?.claims)) {
                factAttribution = citation._grounding.claims
            }
            return
        }
        if (citation?._fact_attribution) {
            factAttribution = Array.isArray(citation._fact_attribution) ? citation._fact_attribution : []
            return
        }
        realCitations.push(citation)
    })

    return {
        citations: realCitations.map((citation: any, index: number) => ({
            ...citation,
            id: String(citation.id || citation.number || `${citation.document_id || 'doc'}-${citation.chunk_id || index}`),
            number: citation.number || index + 1,
            title: citation.title || citation.document_title || citation.document_name || 'Tai lieu nguon',
            description: citation.description || citation.excerpt || citation.citation_excerpt || '',
            excerpt: citation.excerpt || citation.citation_excerpt || citation.snippet || citation.description || '',
            type: citation.type || 'document',
        })),
        grounding,
        factAttribution,
    }
}

const STREAM_RENDER_INTERVAL_MS = 80
const CHAT_MESSAGES_PAGE_SIZE = 500

export const useChat = (options: UseChatOptions = {}) => {
    const { autoFetchConversations = true, canCreateConversations = true, onConversationCreated, onMessageSent } = options
    const { showError, showSuccess } = useToast()

    // State
    const [conversations, setConversations] = useState<ConversationDTO[]>([])
    const [currentConversationId, setCurrentConversationId] = useState<string | undefined>(undefined)
    const [messages, setMessages] = useState<Message[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [isFetchingConversations, setIsFetchingConversations] = useState(false)
    const [userFeedback, setUserFeedback] = useState<Map<string, string>>(new Map())
    const [feedbackLoading, setFeedbackLoading] = useState<Map<string, boolean>>(new Map())
    const [conversationAttachments, setConversationAttachments] =
        useState<ConversationAttachmentViewState>(emptyConversationAttachments)
    const attachmentFetchSeq = useRef(0)

    // Check if we have authentication token
    const hasToken = !!getAuthToken()

    // Fetch conversations
    const fetchConversations = useCallback(async (search?: string) => {
        try {
            setIsFetchingConversations(true)
            logger.debug('Fetching conversations', { search, hasToken })
            const result = await ChatService.getConversations(1, 50, search)
            logger.debug('Conversations fetched', {
                count: result.data?.length || 0,
                total: result.total,
            })
            setConversations(result.data)
        } catch (error) {
            showError('Không thể tải danh sách cuộc trò chuyện')
            logger.error('Failed to fetch conversations', {
                error,
                status: (error as any)?.response?.status,
                data: (error as any)?.response?.data,
            })
        } finally {
            setIsFetchingConversations(false)
        }
    }, [showError, hasToken])

    // Fetch messages for a conversation
    const fetchMessages = useCallback(async (conversationId: string) => {
        try {
            setIsLoading(true)
            let result = await ChatService.getMessages(conversationId, 1, CHAT_MESSAGES_PAGE_SIZE)
            if (result.total > result.pageSize) {
                const latestPage = Math.max(1, Math.ceil(result.total / result.pageSize))
                result = await ChatService.getMessages(conversationId, latestPage, CHAT_MESSAGES_PAGE_SIZE)
            }
            const formattedMessages: Message[] = result.data.map((msg: MessageDTO) => {
                const citationBundle = normalizeCitationBundle(msg.citations)
                return {
                    id: msg.id,
                    role: msg.role,
                    content: msg.content,
                    ...citationBundle,
                    timestamp: new Date(msg.created_at),
                }
            })
            setMessages(formattedMessages)
        } catch (error) {
            logger.error('Failed to fetch messages', error)
            showError('Không thể tải tin nhắn')
        } finally {
            setIsLoading(false)
        }
    }, [showError])

    const fetchConversationAttachments = useCallback(async (conversationId: string) => {
        const requestSeq = attachmentFetchSeq.current + 1
        attachmentFetchSeq.current = requestSeq
        setConversationAttachments(emptyConversationAttachments)

        try {
            const attachments = await ChatService.getConversationAttachments(conversationId)
            if (attachmentFetchSeq.current === requestSeq) {
                setConversationAttachments(mapConversationAttachments(attachments))
            }
            return attachments
        } catch (error) {
            if (attachmentFetchSeq.current === requestSeq) {
                setConversationAttachments(emptyConversationAttachments)
            }
            logger.error('Failed to fetch conversation attachments', error)
            showError('Khong the tai tai lieu dinh kem cua cuoc tro chuyen')
            return null
        }
    }, [showError])

    // Create new conversation
    const createConversation = useCallback(async (title?: string) => {
        if (!canCreateConversations) {
            showError('Bạn không có quyền tạo cuộc trò chuyện mới')
            return null
        }

        try {
            setIsLoading(true)
            const conversation = await ChatService.createConversation(title)
            setConversations((prev) => [conversation, ...prev])
            setCurrentConversationId(conversation.id)
            setMessages([])
            setConversationAttachments(emptyConversationAttachments)
            onConversationCreated?.(conversation)
            showSuccess('Tạo cuộc trò chuyện mới thành công')
            return conversation
        } catch (error) {
            logger.error('Failed to create conversation', error)
            showError('Không thể tạo cuộc trò chuyện mới')
            return null
        } finally {
            setIsLoading(false)
        }
    }, [canCreateConversations, onConversationCreated, showError, showSuccess])

    // Send message (Streaming support)
    const sendMessage = useCallback(
        async (content: string, attachments?: ConversationAttachmentPayload, ragMode: 'fast' | 'deep' = 'fast') => {
            if (!content.trim()) return

            try {
                setIsLoading(true)

                // 1. Quản lý Conversation
                let convId = currentConversationId
                if (!convId) {
                    if (!canCreateConversations) {
                        showError('Bạn không có quyền tạo cuộc trò chuyện mới để gửi tin nhắn')
                        return
                    }

                    const conv = await createConversation(content.substring(0, 50))
                    if (!conv) return
                    convId = conv.id
                }

                if (!convId) return

                const conversationId = convId

                if (attachments?.documentIds?.length || attachments?.folderIds?.length) {
                    const updatedConversation = await ChatService.attachConversationResources(conversationId, {
                        documentIds: attachments.documentIds,
                        folderIds: attachments.folderIds,
                    })
                    attachmentFetchSeq.current += 1
                    setConversationAttachments(mapConversationAttachments(updatedConversation))
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

                // 4. Gọi Stream API — truyền document_ids/folder_ids để backend kích hoạt RAG
                let fullContent = ''
                let renderedContent = ''
                let renderTimer: ReturnType<typeof setTimeout> | null = null

                const updateBotMessage = (patch: Partial<Message>) => {
                    setMessages((prev) =>
                        prev.map(msg => msg.id === botMsgId ? { ...msg, ...patch } : msg)
                    )
                }

                const flushStreamToUI = (force = false) => {
                    if (renderTimer) {
                        if (!force) return
                        clearTimeout(renderTimer)
                        renderTimer = null
                    }

                    if (force) {
                        if (renderedContent !== fullContent) {
                            renderedContent = fullContent
                            updateBotMessage({ content: renderedContent })
                        }
                        return
                    }

                    renderTimer = setTimeout(() => {
                        renderTimer = null
                        if (renderedContent !== fullContent) {
                            renderedContent = fullContent
                            updateBotMessage({ content: renderedContent })
                        }
                    }, STREAM_RENDER_INTERVAL_MS)
                }
                await ChatService.sendMessageStream(
                    content,
                    (chunk) => {
                        fullContent += chunk
                        flushStreamToUI()
                    },
                    conversationId,
                    attachments?.documentIds,
                    attachments?.folderIds,
                    (status) => {
                        // Hiển thị status (VD: "Đang tìm tài liệu...") nếu LLM chưa gửi token nào
                        if (!fullContent) {
                            setMessages((prev) =>
                                prev.map(msg => msg.id === botMsgId ? { ...msg, content: `_⏳ ${status}_` } : msg)
                            )
                        }
                    },
                    (citations) => {
                        flushStreamToUI(true)
                        const citationBundle = normalizeCitationBundle(citations)
                        // Nhận citation data từ backend sau khi stream hoàn tất
                        setMessages((prev) =>
                            prev.map(msg => msg.id === botMsgId
                                ? { ...msg, ...citationBundle }
                                : msg
                            )
                        )
                    },
                    ragMode,
                )
                flushStreamToUI(true)

                // 5. Cập nhật danh sách hội thoại
                // KHÔNG gọi fetchMessages ở đây — backend có thể chưa kịp lưu message
                // xuống DB (xử lý bất đồng bộ), dẫn đến API trả về mảng rỗng và
                // ghi đè mất toàn bộ messages vừa stream. Messages đã có trong state
                // local từ stream; selectConversation sẽ fetch khi cần.
                window.setTimeout(() => {
                    void fetchConversations()
                }, 500)

            } catch (error) {
                logger.error('Streaming error', error)
                showError('Lỗi kết nối máy chủ. Vui lòng thử lại.')
            } finally {
                setIsLoading(false)
            }
        },
        [currentConversationId, createConversation, fetchConversations, showError]
    )

    // Provide feedback
    const sendFeedback = useCallback(async (messageId: string, rating: string, comment?: string) => {
        // Prevent sending feedback for optimistic temporary messages (e.g., bot-123..., user-123...)
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
        if (!uuidRegex.test(messageId)) {
            showError('Tin nhắn chưa được lưu trên máy chủ. Vui lòng đợi vài giây rồi thử lại.')
            return
        }

        try {
            setFeedbackLoading((prev) => new Map(prev).set(messageId, true))
            await ChatService.sendFeedback(messageId, rating, comment)
            setUserFeedback((prev) => new Map(prev).set(messageId, rating))
            showSuccess('Cảm ơn phản hồi của bạn!')
        } catch (error) {
            logger.error('Failed to send feedback', error)
            showError('Không thể gửi phản hồi')
        } finally {
            setFeedbackLoading((prev) => new Map(prev).set(messageId, false))
        }
    }, [showError, showSuccess])

    // Select conversation
    const selectConversation = useCallback(
        (conversationId: string) => {
            setCurrentConversationId(conversationId)
            fetchMessages(conversationId)
            fetchConversationAttachments(conversationId)
        },
        [fetchMessages, fetchConversationAttachments]
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
        userFeedback,
        feedbackLoading,
        conversationAttachments,

        // Actions
        createConversation,
        sendMessage,
        sendFeedback,
        selectConversation,
        fetchConversations,
        fetchMessages,
        fetchConversationAttachments,
        setCurrentConversationId,
    }
}
