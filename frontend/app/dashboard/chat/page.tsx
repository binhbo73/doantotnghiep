'use client'

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { FolderOpen } from 'lucide-react'
import {
    ChatHeader,
    ChatSidebar,
    ChatMessages,
    ChatInput,
} from '@/components/features/chat'
import type { ChatAttachmentState } from '@/components/features/chat/ChatInput'
import { useChat } from '@/hooks/useChat'
import { useAuthContext } from '@/context'
import { useToast } from '@/hooks/useToast'
import { useRBAC } from '@/hooks/useRBAC'

const emptyAttachmentState: ChatAttachmentState = {
    uploads: [],
    selectedDocuments: [],
    selectedFolders: [],
    totalSelected: 0,
}

export default function ChatPage() {
    const router = useRouter()
    const { user, logout, isLoading: authLoading } = useAuthContext()
    const { hasPermission } = useRBAC()
    const { showError } = useToast()
    const [mobileFileDrawerOpen, setMobileFileDrawerOpen] = useState(false)
    const [attachmentState, setAttachmentState] = useState<ChatAttachmentState>(emptyAttachmentState)

    const canReadChats = hasPermission('chat_read')
    const canCreateChats = hasPermission('chat_create')
    const canSendChats = hasPermission('chat_send')
    const canComposeChats = canSendChats && (canReadChats || canCreateChats)
    const canUseChatPage = canReadChats || canCreateChats

    // Chat hook for managing chat state
    const {
        conversations,
        currentConversationId,
        messages,
        isLoading,
        isFetchingConversations,
        userFeedback,
        feedbackLoading,
        conversationAttachments,
        createConversation,
        sendMessage,
        sendFeedback,
        selectConversation,
    } = useChat({
        autoFetchConversations: !!user && canReadChats, // Only fetch if user may read chats
        canCreateConversations: canCreateChats,
        onConversationCreated: (conversation) => {
            console.log('New conversation created:', conversation.id)
        },
        onMessageSent: (message) => {
            console.log('Message sent:', message.id)
        },
    })

    const systemDocumentCount = new Set([
        ...conversationAttachments.documents.map((item) => item.id),
        ...attachmentState.selectedDocuments.map((item) => item.id),
    ]).size
    const systemFolderCount = new Set([
        ...conversationAttachments.folders.map((item) => item.id),
        ...attachmentState.selectedFolders.map((item) => item.id),
    ]).size
    const totalFileAttachments = systemDocumentCount + systemFolderCount + attachmentState.uploads.length

    // Redirect to login if not authenticated
    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login')
        }
    }, [user, router, authLoading])

    useEffect(() => {
        setAttachmentState(emptyAttachmentState)
    }, [currentConversationId])

    const handleLogout = async () => {
        try {
            await logout()
            router.push('/login')
        } catch (error) {
            showError('Không thể đăng xuất')
            console.error('Logout error:', error)
        }
    }

    // Show loading state while checking authentication
    if (authLoading || !user) {
        return (
            <div className="flex items-center justify-center h-screen bg-surface dark:bg-slate-950">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
                    <p className="text-slate-600 dark:text-slate-400">Đang tải...</p>
                </div>
            </div>
        )
    }

    if (!canUseChatPage) {
        return (
            <div className="flex items-center justify-center h-screen bg-surface dark:bg-slate-950 px-4">
                <div className="max-w-lg text-center rounded-3xl border border-slate-200 bg-white p-10 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                    <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Không có quyền truy cập Chat</p>
                    <p className="mt-4 text-sm leading-6 text-slate-600 dark:text-slate-400">
                        Bạn không có quyền xem hoặc sử dụng tính năng Chat. Vui lòng liên hệ quản trị viên để được cấp quyền.
                    </p>
                </div>
            </div>
        )
    }

    return (
        <div className="flex flex-col h-screen w-full bg-surface dark:bg-slate-950">
            {/* Header */}
            <ChatHeader
                title="Tri thức Doanh nghiệp"
                onLogout={handleLogout}
            />

            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar */}
                <ChatSidebar
                    conversations={conversations}
                    selectedConversationId={currentConversationId || undefined}
                    attachmentState={attachmentState}
                    conversationAttachments={conversationAttachments}
                    mobileFileDrawerOpen={mobileFileDrawerOpen}
                    onCloseMobileFileDrawer={() => setMobileFileDrawerOpen(false)}
                    isLoading={isFetchingConversations}
                    onNewChat={() => createConversation()}
                    onSelectConversation={selectConversation}
                    onLogout={handleLogout}
                />

                {/* Main Chat Area */}
                <main className="flex-1 flex flex-col overflow-hidden bg-surface dark:bg-slate-950">
                    <div className="md:hidden px-4 pt-3 pb-1">
                        <button
                            type="button"
                            onClick={() => setMobileFileDrawerOpen(true)}
                            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm font-semibold text-slate-700 dark:text-slate-200"
                        >
                            <FolderOpen size={16} className="text-amber-600" />
                            File đính kèm {totalFileAttachments > 0 ? `(${totalFileAttachments})` : ''}
                        </button>
                    </div>

                    {/* Messages */}
                    <ChatMessages
                        messages={messages}
                        isLoading={isLoading}
                        onFeedback={sendFeedback}
                        userFeedback={userFeedback}
                        feedbackLoading={feedbackLoading}
                        onCopy={(content) => {
                            navigator.clipboard.writeText(content)
                        }}
                    />

                    {/* Input */}
                    <ChatInput
                        key={currentConversationId || 'new-chat'}
                        isLoading={isLoading}
                        disabled={!canComposeChats}
                        onAttachmentStateChange={setAttachmentState}
                        onSendMessage={(content, attachments) => {
                            sendMessage(content, attachments)
                        }}
                    />
                </main>
            </div>
        </div>
    )
}
