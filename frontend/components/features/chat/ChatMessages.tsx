'use client'

import React from 'react'
import { Zap, ThumbsUp, ThumbsDown, Copy, Share2 } from 'lucide-react'
import { KnowledgeCard } from './KnowledgeCard'

export interface Message {
    id: string
    role: 'user' | 'assistant'
    content: string
    citations?: {
        id: string
        title: string
        description?: string
        page?: string | number
        type?: 'pdf' | 'document' | 'article'
    }[]
    timestamp?: Date
    isLoading?: boolean
}

interface ChatMessagesProps {
    messages?: Message[]
    isLoading?: boolean
    onFeedback?: (messageId: string, helpful: boolean) => void
    onCopy?: (content: string) => void
}

export const ChatMessages: React.FC<ChatMessagesProps> = ({
    messages = [],
    isLoading = false,
    onFeedback,
    onCopy,
}) => {
    return (
        <div className="flex-1 overflow-y-auto p-6 md:p-12 space-y-10">
            {messages.length === 0 && !isLoading && (
                <div className="flex flex-col items-center justify-center h-full text-center">
                    <Zap size={48} className="text-primary/20 mb-4" />
                    <h2 className="text-xl font-semibold text-slate-600 dark:text-slate-300 mb-2">
                        Bắt đầu một cuộc trò chuyện
                    </h2>
                    <p className="text-slate-500 dark:text-slate-400 max-w-sm">
                        Hỏi các câu hỏi về tài liệu và tri thức nội bộ của bạn. Tôi sẽ giúp bạn tìm câu trả lời.
                    </p>
                </div>
            )}

            {messages.map((message, index) => (
                <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} items-start gap-4`}>
                    {message.role === 'assistant' && (
                        <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shrink-0 shadow-lg shadow-primary/20">
                            <Zap size={20} className="text-on-primary" />
                        </div>
                    )}

                    <div className={`flex-1 ${message.role === 'user' ? 'max-w-lg' : 'max-w-5xl'}`}>
                        {message.role === 'user' ? (
                            <div className="bg-primary-container text-on-primary-container p-4 rounded-2xl rounded-tr-none shadow-sm text-sm font-medium leading-relaxed">
                                {message.content}
                            </div>
                        ) : (
                            <div className="glass-nugget p-6 rounded-2xl shadow-sm space-y-4 bg-white/70 dark:bg-slate-800/70 backdrop-blur-sm border border-outline-variant/10 dark:border-slate-700/20">
                                <div className="prose prose-sm dark:prose-invert max-w-none">
                                    {message.isLoading ? (
                                        <div className="space-y-3">
                                            {[1, 2, 3].map((i) => (
                                                <div
                                                    key={i}
                                                    className="h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse"
                                                    style={{ width: `${Math.random() * 40 + 60}%` }}
                                                />
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-on-surface dark:text-slate-100 leading-relaxed whitespace-pre-wrap">
                                            {message.content}
                                        </p>
                                    )}
                                </div>

                                {message.citations && message.citations.length > 0 && (
                                    <KnowledgeCard
                                        citations={message.citations}
                                        isLoading={message.isLoading}
                                    />
                                )}

                                {!message.isLoading && (
                                    <div className="flex items-center justify-between pt-2">
                                        <div className="flex items-center gap-4">
                                            <button
                                                onClick={() => onFeedback?.(message.id, true)}
                                                className="flex items-center gap-1.5 text-[11px] font-bold text-slate-500 hover:text-primary transition-colors"
                                            >
                                                <ThumbsUp size={16} />
                                                Hữu ích
                                            </button>
                                            <button
                                                onClick={() => onFeedback?.(message.id, false)}
                                                className="flex items-center gap-1.5 text-[11px] font-bold text-slate-500 hover:text-error transition-colors"
                                            >
                                                <ThumbsDown size={16} />
                                                Không hữu ích
                                            </button>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={() => onCopy?.(message.content)}
                                                className="p-2 text-slate-400 hover:text-primary transition-colors rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                                                title="Copy"
                                            >
                                                <Copy size={16} />
                                            </button>
                                            <button className="p-2 text-slate-400 hover:text-primary transition-colors rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800" title="Share">
                                                <Share2 size={16} />
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {message.role === 'user' && (
                        <div className="w-8 h-8 rounded-lg bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center shrink-0">
                            <span className="text-orange-600 dark:text-orange-400 text-sm font-bold">A</span>
                        </div>
                    )}
                </div>
            ))}

            {isLoading && (
                <div className="flex justify-start items-center gap-4 opacity-50">
                    <div className="w-10 h-10 rounded-xl bg-slate-200 dark:bg-slate-700 animate-pulse" />
                    <div className="h-4 w-32 bg-slate-200 dark:bg-slate-700 rounded-full animate-pulse" />
                </div>
            )}
        </div>
    )
}
