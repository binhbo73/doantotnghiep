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
import { ChatAttachmentState } from '@/components/features/chat/ChatInput'
import { useChat } from '@/hooks/useChat'
import { useAuthContext } from '@/context'
import { useToast } from '@/hooks/useToast'

export default function ChatPage() {
    const router = useRouter()
    const { user, logout, isLoading: authLoading } = useAuthContext()
    const { showError } = useToast()
    const [mobileFileDrawerOpen, setMobileFileDrawerOpen] = useState(false)
    const [attachmentState, setAttachmentState] = useState<ChatAttachmentState>({
        uploads: [],
        selectedDocuments: [],
        selectedFolders: [],
        totalSelected: 0,
    })

    // Chat hook for managing chat state
    const {
        conversations,
        currentConversationId,
        messages,
        isLoading,
        isFetchingConversations,
        userFeedback,
        feedbackLoading,
        createConversation,
        sendMessage,
        sendFeedback,
        selectConversation,
    } = useChat({
        autoFetchConversations: !!user, // Only fetch when user is authenticated
        onConversationCreated: (conversation) => {
            console.log('New conversation created:', conversation.id)
        },
        onMessageSent: (message) => {
            console.log('Message sent:', message.id)
        },
    })

    // Redirect to login if not authenticated
    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login')
        }
    }, [user, router, authLoading])

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
                            File đính kèm {attachmentState.totalSelected > 0 ? `(${attachmentState.totalSelected})` : ''}
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
                        isLoading={isLoading}
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
