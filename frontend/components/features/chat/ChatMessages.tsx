'use client'

import React, { useState } from 'react'
import { formatRelativeTime, formatAbsoluteShort } from '@/lib/time'
import { Zap, Star, Copy, Share2, Loader } from 'lucide-react'
import { KnowledgeCard } from './KnowledgeCard'
import { useFeedback } from '@/hooks/useFeedback'
import { useToast } from '@/hooks/useToast'

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
    onCopy?: (content: string) => void
    onFeedback?: (messageId: string, rating: string, comment?: string) => Promise<void>
    userFeedback?: Map<string, string>
    feedbackLoading?: Map<string, boolean>
}

export const ChatMessages: React.FC<ChatMessagesProps> = ({
    messages = [],
    isLoading = false,
    onCopy,
    onFeedback,
    userFeedback: propUserFeedback,
    feedbackLoading: propFeedbackLoading,
}) => {
    const { submitFeedback, userFeedback: internalUserFeedback, loading: internalFeedbackLoading } = useFeedback()
    const userFeedback = propUserFeedback || internalUserFeedback
    const feedbackLoading = propFeedbackLoading || internalFeedbackLoading
    const { toast } = useToast()
    const [feedbackComments, setFeedbackComments] = useState<Map<string, string>>(new Map())
    const [showCommentBox, setShowCommentBox] = useState<string | null>(null)
    const [currentRating, setCurrentRating] = useState<string | null>(null)
    const [hoveredStar, setHoveredStar] = useState<{ [messageId: string]: number }>({})

    const formatMessageTime = (timestamp?: Date) => {
        return formatRelativeTime(timestamp)
    }

    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

    const handleFeedback = async (messageId: string, rating: string, forceSubmit: boolean = false) => {
        // For star rating, we might want to show comment box immediately after rating
        if (!showCommentBox && !forceSubmit) {
            setShowCommentBox(messageId)
            setCurrentRating(rating)
            return
        }

        try {
            const comment = feedbackComments.get(messageId)?.trim()
            const normalizedRating: 'upvote' | 'downvote' = rating === 'downvote' ? 'downvote' : 'upvote'
            if (onFeedback) {
                await onFeedback(messageId, rating, comment)
            } else {
                await submitFeedback(messageId, normalizedRating, comment)
            }

            // Success!
            setShowCommentBox(null)
            setCurrentRating(null)
        } catch (err) {
            console.error('Failed to submit feedback:', err)
        }
    }

    const handleCopy = (content: string) => {
        navigator.clipboard.writeText(content)
        toast({
            title: 'Copied',
            description: 'Message copied to clipboard',
            type: 'success',
        })
        onCopy?.(content)
    }

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
                            <div className="space-y-2">
                                <div className="bg-primary-container text-on-primary-container p-4 rounded-2xl rounded-tr-none shadow-sm text-sm font-medium leading-relaxed">
                                    {message.content}
                                </div>
                                {message.timestamp && (
                                    <p className="px-1 text-[11px] text-slate-400 text-right" title={formatAbsoluteShort(message.timestamp)}>
                                        {formatMessageTime(message.timestamp)}
                                    </p>
                                )}
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

                                {message.timestamp && !message.isLoading && (
                                    <p className="text-[11px] text-slate-400" title={formatAbsoluteShort(message.timestamp)}>
                                        {formatMessageTime(message.timestamp)}
                                    </p>
                                )}

                                {message.citations && message.citations.length > 0 && (
                                    <KnowledgeCard
                                        citations={message.citations}
                                        isLoading={message.isLoading}
                                    />
                                )}

                                {!message.isLoading && (
                                    <div className="space-y-3 pt-2">
                                        <div className="flex items-center justify-between">
                                            <div className="flex flex-col gap-3">
                                                <div className="flex items-center gap-1">
                                                    {[1, 2, 3, 4, 5].map((star) => {
                                                        const isSelected = (parseInt(userFeedback.get(message.id) || '0')) >= star || (parseInt(currentRating || '0')) >= star;
                                                        const isHovered = (hoveredStar[message.id] || 0) >= star;

                                                        return (
                                                            <button
                                                                key={star}
                                                                onMouseEnter={() => setHoveredStar(prev => ({ ...prev, [message.id]: star }))}
                                                                onMouseLeave={() => setHoveredStar(prev => ({ ...prev, [message.id]: 0 }))}
                                                                onClick={() => {
                                                                    if (!uuidRegex.test(message.id)) {
                                                                        toast({ title: 'Chờ lưu', description: 'Tin nhắn chưa được lưu trên máy chủ. Vui lòng đợi rồi thử lại.', type: 'info' })
                                                                        return
                                                                    }
                                                                    handleFeedback(message.id, star.toString())
                                                                }}
                                                                disabled={feedbackLoading.get(message.id) || !uuidRegex.test(message.id)}
                                                                className="p-1 transition-all transform hover:scale-110 active:scale-95 disabled:opacity-50"
                                                            >
                                                                <Star
                                                                    size={18}
                                                                    className={`${isHovered || isSelected
                                                                        ? 'text-amber-400 fill-amber-400'
                                                                        : 'text-slate-300 dark:text-slate-600 hover:text-amber-200'
                                                                        } transition-colors duration-200`}
                                                                />
                                                            </button>
                                                        )
                                                    })}
                                                    <span className="ml-2 text-[10px] text-slate-400 font-medium">
                                                        {userFeedback.get(message.id) ? 'Đã đánh giá' : 'Đánh giá câu trả lời này'}
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => handleCopy(message.content)}
                                                    className="p-2 text-slate-400 hover:text-primary transition-colors rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                                                    title="Copy message"
                                                >
                                                    <Copy size={16} />
                                                </button>
                                                <button
                                                    onClick={() => {
                                                        if (navigator.share) {
                                                            navigator.share({
                                                                title: 'AI Response',
                                                                text: message.content,
                                                                url: window.location.href,
                                                            })
                                                        } else {
                                                            toast({
                                                                title: 'Sharing not supported',
                                                                description: 'Your browser does not support native sharing.',
                                                                variant: 'destructive',
                                                            })
                                                        }
                                                    }}
                                                    className="p-2 text-slate-400 hover:text-primary transition-colors rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                                                    title="Share message"
                                                >
                                                    <Share2 size={16} />
                                                </button>
                                            </div>
                                        </div>

                                        {/* Feedback Comment Box */}
                                        {showCommentBox === message.id && (
                                            <div className="mt-3 p-3 bg-slate-100 dark:bg-slate-700 rounded-lg space-y-2">
                                                <textarea
                                                    value={feedbackComments.get(message.id) || ''}
                                                    onChange={(e) =>
                                                        setFeedbackComments((prev) => new Map(prev).set(message.id, e.target.value))
                                                    }
                                                    placeholder="Hãy cho chúng tôi biết lý do (tùy chọn)..."
                                                    maxLength={1000}
                                                    className="w-full p-3 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-rose-500/50 focus:border-rose-500/50 transition-all resize-none"
                                                    rows={3}
                                                />
                                                <div className="flex gap-2 justify-end">
                                                    <button
                                                        onClick={() => setShowCommentBox(null)}
                                                        className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                                                    >
                                                        Hủy
                                                    </button>
                                                    <button
                                                        onClick={() => {
                                                            if (!uuidRegex.test(message.id)) {
                                                                toast({ title: 'Chờ lưu', description: 'Tin nhắn chưa được lưu trên máy chủ. Vui lòng đợi rồi thử lại.', type: 'info' })
                                                                return
                                                            }
                                                            const rating = currentRating || userFeedback.get(message.id) || '5'
                                                            handleFeedback(message.id, rating, true)
                                                        }}
                                                        disabled={feedbackLoading.get(message.id) || !uuidRegex.test(message.id)}
                                                        className="px-4 py-1.5 text-xs font-semibold bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors shadow-sm shadow-amber-200 dark:shadow-none disabled:opacity-50"
                                                    >
                                                        {feedbackLoading.get(message.id) ? 'Đang gửi...' : 'Gửi đánh giá'}
                                                    </button>
                                                </div>
                                            </div>
                                        )}
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
