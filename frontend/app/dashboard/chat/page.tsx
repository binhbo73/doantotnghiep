'use client'

import React, { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
    ChatHeader,
    ChatSidebar,
    ChatMessages,
    ChatInput,
} from '@/components/features/chat'
import { useChat } from '@/hooks/useChat'
import { useAuthContext } from '@/context'
import { useToast } from '@/hooks/useToast'

export default function ChatPage() {
    const router = useRouter()
    const { user, logout, isLoading: authLoading } = useAuthContext()
    const { showError } = useToast()

    // Chat hook for managing chat state
    const {
        conversations,
        currentConversationId,
        messages,
        isLoading,
        isFetchingConversations,
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
                    isLoading={isFetchingConversations}
                    onNewChat={() => createConversation()}
                    onSelectConversation={selectConversation}
                    onLogout={handleLogout}
                />

                {/* Main Chat Area */}
                <main className="flex-1 flex flex-col overflow-hidden bg-surface dark:bg-slate-950">
                    {/* Messages */}
                    <ChatMessages
                        messages={messages}
                        isLoading={isLoading}
                        onFeedback={sendFeedback}
                        onCopy={(content) => {
                            navigator.clipboard.writeText(content)
                        }}
                    />

                    {/* Input */}
                    <ChatInput
                        isLoading={isLoading}
                        onSendMessage={(content, attachments) => {
                            const files = attachments ? [] : undefined
                            sendMessage(content, files)
                        }}
                    />
                </main>
            </div>
        </div>
    )
}
