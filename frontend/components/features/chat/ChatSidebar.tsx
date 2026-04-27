'use client'

import React, { useState, useEffect } from 'react'
import { Plus, MessageCircle, Zap, LogOut, HelpCircle } from 'lucide-react'

interface Conversation {
    id: string
    title: string
    createdAt: string
    updatedAt: string
}

interface ChatSidebarProps {
    conversations?: Conversation[]
    selectedConversationId?: string
    onNewChat?: () => void
    onSelectConversation?: (id: string) => void
    onLogout?: () => void
    isLoading?: boolean
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
    conversations = [],
    selectedConversationId,
    onNewChat,
    onSelectConversation,
    onLogout,
    isLoading = false,
}) => {
    const [groupedConversations, setGroupedConversations] = useState<{
        today: Conversation[]
        week: Conversation[]
        older: Conversation[]
    }>({ today: [], week: [], older: [] })

    useEffect(() => {
        if (conversations.length === 0) return

        const now = new Date()
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
        const weekAgo = new Date(today)
        weekAgo.setDate(weekAgo.getDate() - 7)

        const grouped = {
            today: [] as Conversation[],
            week: [] as Conversation[],
            older: [] as Conversation[],
        }

        conversations.forEach((conv) => {
            const convDate = new Date(conv.updatedAt)
            const convDateOnly = new Date(convDate.getFullYear(), convDate.getMonth(), convDate.getDate())

            if (convDateOnly.getTime() >= today.getTime()) {
                grouped.today.push(conv)
            } else if (convDateOnly.getTime() >= weekAgo.getTime()) {
                grouped.week.push(conv)
            } else {
                grouped.older.push(conv)
            }
        })

        setGroupedConversations(grouped)
    }, [conversations])

    const renderConversationGroup = (title: string, convs: Conversation[]) => {
        if (convs.length === 0) return null

        return (
            <div key={title} className="mb-4">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-2 mb-3">
                    {title}
                </p>
                <div className="space-y-1">
                    {convs.map((conv) => (
                        <button
                            key={conv.id}
                            onClick={() => onSelectConversation?.(conv.id)}
                            className={`w-full text-left p-3 rounded-xl text-sm truncate flex items-center gap-2 transition-all ${selectedConversationId === conv.id
                                ? 'bg-primary/10 text-primary font-semibold border border-primary/20'
                                : 'text-slate-600 hover:bg-white dark:hover:bg-slate-800 dark:text-slate-400'
                                }`}
                            title={conv.title}
                        >
                            <MessageCircle size={16} className="shrink-0" />
                            <span className="truncate">{conv.title}</span>
                        </button>
                    ))}
                </div>
            </div>
        )
    }

    return (
        <aside className="w-72 bg-surface-container-low dark:bg-slate-900 flex flex-col border-r border-outline-variant/10 overflow-hidden">
            <div className="p-6 border-b border-outline-variant/10">
                <button
                    onClick={onNewChat}
                    disabled={isLoading}
                    className="w-full py-3 px-4 bg-primary text-on-primary rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-primary/20 active:scale-95 transition-transform disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg hover:shadow-primary/30"
                >
                    <Plus size={18} />
                    Trò chuyện mới
                </button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
                {isLoading ? (
                    <div className="space-y-2">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="h-10 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
                        ))}
                    </div>
                ) : conversations.length === 0 ? (
                    <div className="text-center text-slate-400 text-sm py-8">
                        <MessageCircle size={24} className="mx-auto mb-2 opacity-50" />
                        <p>Chưa có cuộc trò chuyện</p>
                    </div>
                ) : (
                    <>
                        {renderConversationGroup('Hôm nay', groupedConversations.today)}
                        {renderConversationGroup('7 ngày trước', groupedConversations.week)}
                        {renderConversationGroup('Cũ hơn', groupedConversations.older)}
                    </>
                )}
            </div>

        </aside>
    )
}
