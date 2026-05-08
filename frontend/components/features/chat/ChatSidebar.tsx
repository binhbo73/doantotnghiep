'use client'

import React, { useState, useEffect } from 'react'
import { Plus, MessageCircle, FolderOpen, FileText, Paperclip, Check, X } from 'lucide-react'
import { ChatAttachmentState } from './ChatInput'

interface Conversation {
    id: string
    title: string
    // backend returns snake_case; frontend may use camelCase — accept both
    createdAt?: string
    updatedAt?: string
    created_at?: string
    updated_at?: string
}

interface ChatSidebarProps {
    conversations?: Conversation[]
    selectedConversationId?: string
    attachmentState?: ChatAttachmentState
    mobileFileDrawerOpen?: boolean
    onCloseMobileFileDrawer?: () => void
    onNewChat?: () => void
    onSelectConversation?: (id: string) => void
    onLogout?: () => void
    isLoading?: boolean
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
    conversations = [],
    selectedConversationId,
    attachmentState,
    mobileFileDrawerOpen = false,
    onCloseMobileFileDrawer,
    onNewChat,
    onSelectConversation,
    onLogout,
    isLoading = false,
}) => {
    const [activeTab, setActiveTab] = useState<'conversations' | 'files'>('conversations')
    const [uncheckedKeys, setUncheckedKeys] = useState<Set<string>>(new Set())
    const [groupedConversations, setGroupedConversations] = useState<{
        today: Conversation[]
        week: Conversation[]
        older: Conversation[]
    }>({ today: [], week: [], older: [] })

    const { formatRelativeTime } = require('@/lib/time') as typeof import('@/lib/time')
    const formatConversationTime = (timestamp?: string) => {
        return formatRelativeTime(timestamp || '')
    }

    const formatFileSize = (bytes: number) => {
        if (!bytes || bytes <= 0) return '0 B'
        const k = 1024
        const sizes = ['B', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return `${Math.round((bytes / Math.pow(k, i)) * 10) / 10} ${sizes[i]}`
    }

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
            const convDate = new Date(conv.updatedAt || conv.updated_at || new Date().toISOString())
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
                            <span className="flex-1 min-w-0 truncate">{conv.title}</span>
                            <span className="shrink-0 text-[10px] text-slate-400 font-medium">
                                {formatConversationTime(conv.updatedAt || conv.updated_at)}
                            </span>
                        </button>
                    ))}
                </div>
            </div>
        )
    }

    const totalAttached = attachmentState?.totalSelected || 0

    const isChecked = (key: string) => !uncheckedKeys.has(key)
    const toggleChecked = (key: string) => {
        setUncheckedKeys((prev) => {
            const next = new Set(prev)
            if (next.has(key)) {
                next.delete(key)
            } else {
                next.add(key)
            }
            return next
        })
    }

    const renderFileContent = () => (
        <div className="space-y-5">
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/70 p-3">
                <p className="text-[11px] uppercase tracking-wider font-bold text-slate-500">Nguồn đã chọn</p>
                <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">
                    {attachmentState?.selectedDocuments.length || 0} tài liệu, {attachmentState?.selectedFolders.length || 0} thư mục, {attachmentState?.uploads.length || 0} tệp tải lên
                </p>
                {totalAttached > 0 && (
                    <button
                        type="button"
                        onClick={() => attachmentState?.clearAll?.()}
                        className="mt-2 text-xs font-semibold text-slate-500 hover:text-red-500"
                    >
                        Bỏ chọn tất cả
                    </button>
                )}
            </div>

            {attachmentState?.uploads.length ? (
                <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1 mb-2">Tệp tải lên</p>
                    <div className="space-y-2">
                        {attachmentState.uploads.map((upload) => (
                            (() => {
                                const key = `upload-${upload.id}`
                                const checked = isChecked(key)
                                return (
                                    <div key={upload.id} className="rounded-xl border border-slate-200 dark:border-slate-700 p-3 bg-white dark:bg-slate-800">
                                        <div className="flex items-start gap-2">
                                            <Paperclip size={14} className="mt-1 text-slate-400 shrink-0" />
                                            <div className="min-w-0 flex-1">
                                                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{upload.name}</p>
                                                <p className="text-[11px] text-slate-500 mt-0.5">{formatFileSize(upload.size)}</p>
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                                <button
                                                    type="button"
                                                    onClick={() => toggleChecked(key)}
                                                    className={`w-5 h-5 rounded-md flex items-center justify-center shadow-sm transition-colors ${checked
                                                        ? 'border border-orange-500 bg-orange-500 text-white'
                                                        : 'border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-transparent'
                                                        }`}
                                                    title={checked ? 'Bỏ tick' : 'Tick chọn'}
                                                >
                                                    <Check size={12} />
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => attachmentState?.removeUpload?.(upload.id)}
                                                    className="p-1 rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30"
                                                    title="Xóa tệp đính kèm"
                                                >
                                                    <X size={12} />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                )
                            })()
                        ))}
                    </div>
                </div>
            ) : null}

            {attachmentState?.selectedDocuments.length ? (
                <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1 mb-2">Tài liệu hệ thống</p>
                    <div className="space-y-2">
                        {attachmentState.selectedDocuments.map((doc) => (
                            (() => {
                                const key = `doc-${doc.id}`
                                const checked = isChecked(key)
                                return (
                                    <div key={doc.id} className="rounded-xl border border-slate-200 dark:border-slate-700 p-3 bg-white dark:bg-slate-800">
                                        <div className="flex items-start gap-2">
                                            <FileText size={14} className="mt-1 text-slate-400 shrink-0" />
                                            <div className="min-w-0 flex-1">
                                                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{doc.name}</p>
                                                <p className="text-[11px] text-slate-500 mt-0.5 capitalize">{doc.detail || 'document'}</p>
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                                <button
                                                    type="button"
                                                    onClick={() => toggleChecked(key)}
                                                    className={`w-5 h-5 rounded-md flex items-center justify-center shadow-sm transition-colors ${checked
                                                        ? 'border border-blue-500 bg-blue-500 text-white'
                                                        : 'border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-transparent'
                                                        }`}
                                                    title={checked ? 'Bỏ tick' : 'Tick chọn'}
                                                >
                                                    <Check size={12} />
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => attachmentState?.removeDocument?.(doc.id)}
                                                    className="p-1 rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30"
                                                    title="Bỏ tài liệu"
                                                >
                                                    <X size={12} />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                )
                            })()
                        ))}
                    </div>
                </div>
            ) : null}

            {attachmentState?.selectedFolders.length ? (
                <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1 mb-2">Thư mục hệ thống</p>
                    <div className="space-y-2">
                        {attachmentState.selectedFolders.map((folder) => (
                            (() => {
                                const key = `folder-${folder.id}`
                                const checked = isChecked(key)
                                return (
                                    <div key={folder.id} className="rounded-xl border border-slate-200 dark:border-slate-700 p-3 bg-white dark:bg-slate-800">
                                        <div className="flex items-start gap-2">
                                            <FolderOpen size={14} className="mt-1 text-amber-600 shrink-0" />
                                            <div className="min-w-0 flex-1">
                                                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{folder.name}</p>
                                                <p className="text-[11px] text-slate-500 mt-0.5 capitalize">{folder.detail || 'folder'}</p>
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                                <button
                                                    type="button"
                                                    onClick={() => toggleChecked(key)}
                                                    className={`w-5 h-5 rounded-md flex items-center justify-center shadow-sm transition-colors ${checked
                                                        ? 'border border-emerald-500 bg-emerald-500 text-white'
                                                        : 'border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-transparent'
                                                        }`}
                                                    title={checked ? 'Bỏ tick' : 'Tick chọn'}
                                                >
                                                    <Check size={12} />
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => attachmentState?.removeFolder?.(folder.id)}
                                                    className="p-1 rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30"
                                                    title="Bỏ thư mục"
                                                >
                                                    <X size={12} />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                )
                            })()
                        ))}
                    </div>
                </div>
            ) : null}

            {totalAttached === 0 ? (
                <div className="text-center text-slate-400 text-sm py-10">
                    <FolderOpen size={24} className="mx-auto mb-2 opacity-50" />
                    <p>Chưa có tài liệu nào được đính kèm</p>
                </div>
            ) : null}
        </div>
    )

    return (
        <>
            <aside className="hidden md:flex w-80 bg-surface-container-low dark:bg-slate-900 flex-col border-r border-outline-variant/10 overflow-hidden">
                <div className="p-6 border-b border-outline-variant/10">
                    <button
                        onClick={onNewChat}
                        disabled={isLoading}
                        className="w-full py-3 px-4 bg-primary text-on-primary rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-primary/20 active:scale-95 transition-transform disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg hover:shadow-primary/30"
                    >
                        <Plus size={18} />
                        Trò chuyện mới
                    </button>

                    <div className="mt-4 rounded-xl bg-slate-100 dark:bg-slate-800 p-1 flex items-center gap-1">
                        <button
                            type="button"
                            onClick={() => setActiveTab('conversations')}
                            className={`flex-1 py-2 px-3 rounded-lg text-sm font-semibold transition-colors ${activeTab === 'conversations'
                                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm'
                                : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                                }`}
                        >
                            Trò chuyện
                        </button>
                        <button
                            type="button"
                            onClick={() => setActiveTab('files')}
                            className={`flex-1 py-2 px-3 rounded-lg text-sm font-semibold transition-colors ${activeTab === 'files'
                                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm'
                                : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                                }`}
                        >
                            File {totalAttached > 0 ? `(${totalAttached})` : ''}
                        </button>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
                    {activeTab === 'conversations' ? (
                        isLoading ? (
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
                        )
                    ) : (
                        renderFileContent()
                    )}
                </div>

            </aside>

            {mobileFileDrawerOpen && (
                <div className="md:hidden fixed inset-0 z-50 bg-slate-950/45 backdrop-blur-sm">
                    <button
                        type="button"
                        aria-label="Đóng drawer"
                        className="absolute inset-0"
                        onClick={onCloseMobileFileDrawer}
                    />

                    <div className="absolute inset-y-0 right-0 w-[88vw] max-w-sm bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700 shadow-2xl flex flex-col">
                        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
                            <div>
                                <p className="text-sm font-bold text-slate-900 dark:text-slate-100">Nguồn đính kèm</p>
                                <p className="text-xs text-slate-500">Tab File trên mobile</p>
                            </div>
                            <button
                                type="button"
                                onClick={onCloseMobileFileDrawer}
                                className="p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800"
                                title="Đóng"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto px-4 py-4">
                            {renderFileContent()}
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}
