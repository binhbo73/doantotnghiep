/**
 * FeedbackWidget Component - Feedback buttons with optional comment modal
 * 
 * Features:
 * - Upvote/Downvote buttons
 * - Optional comment box
 * - Loading states
 * - Visual feedback for selected rating
 */

'use client'

import React, { useState } from 'react'
import { ThumbsUp, ThumbsDown, Loader } from 'lucide-react'

interface FeedbackWidgetProps {
    messageId: string
    onSubmit: (rating: 'upvote' | 'downvote', comment?: string) => Promise<void>
    userRating?: 'upvote' | 'downvote' | null
    isLoading?: boolean
    showCommentBox?: boolean
}

export const FeedbackWidget: React.FC<FeedbackWidgetProps> = ({
    messageId,
    onSubmit,
    userRating,
    isLoading = false,
    showCommentBox: initialShowComment = false,
}) => {
    const [comment, setComment] = useState('')
    const [showComment, setShowComment] = useState(initialShowComment)
    const [selectedRating, setSelectedRating] = useState<'upvote' | 'downvote' | null>(userRating || null)

    const handleRatingClick = async (rating: 'upvote' | 'downvote') => {
        setSelectedRating(rating)
        if (!comment.trim()) {
            // Submit immediately without comment
            await onSubmit(rating)
        } else {
            // Show comment box first
            setShowComment(true)
        }
    }

    const handleSubmit = async () => {
        if (selectedRating) {
            await onSubmit(selectedRating, comment.trim() || undefined)
            setComment('')
            setShowComment(false)
        }
    }

    const handleCancel = () => {
        setComment('')
        setShowComment(false)
        setSelectedRating(userRating || null)
    }

    return (
        <div className="space-y-2">
            <div className="flex items-center gap-3">
                <button
                    onClick={() => handleRatingClick('upvote')}
                    disabled={isLoading}
                    className={`flex items-center gap-1.5 text-[11px] font-bold transition-colors rounded px-2 py-1 ${selectedRating === 'upvote'
                            ? 'text-primary bg-primary/10'
                            : 'text-slate-500 hover:text-primary hover:bg-slate-100 dark:hover:bg-slate-700'
                        } disabled:opacity-50 disabled:cursor-not-allowed`}
                    title="Mark as helpful"
                >
                    {isLoading && selectedRating === 'upvote' ? (
                        <Loader size={16} className="animate-spin" />
                    ) : (
                        <ThumbsUp size={16} fill={selectedRating === 'upvote' ? 'currentColor' : 'none'} />
                    )}
                    Hữu ích
                </button>

                <button
                    onClick={() => handleRatingClick('downvote')}
                    disabled={isLoading}
                    className={`flex items-center gap-1.5 text-[11px] font-bold transition-colors rounded px-2 py-1 ${selectedRating === 'downvote'
                            ? 'text-error bg-error/10'
                            : 'text-slate-500 hover:text-error hover:bg-slate-100 dark:hover:bg-slate-700'
                        } disabled:opacity-50 disabled:cursor-not-allowed`}
                    title="Mark as not helpful"
                >
                    {isLoading && selectedRating === 'downvote' ? (
                        <Loader size={16} className="animate-spin" />
                    ) : (
                        <ThumbsDown size={16} fill={selectedRating === 'downvote' ? 'currentColor' : 'none'} />
                    )}
                    Không hữu ích
                </button>
            </div>

            {showComment && (
                <div className="p-3 bg-slate-100 dark:bg-slate-700 rounded-lg space-y-2 animate-in fade-in slide-in-from-top-2 duration-200">
                    <textarea
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        placeholder="Add optional comment about your feedback (max 1000 characters)..."
                        maxLength={1000}
                        autoFocus
                        className="w-full p-2 text-sm bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary"
                        rows={3}
                    />
                    <div className="flex gap-2 justify-end">
                        <button
                            onClick={handleCancel}
                            disabled={isLoading}
                            className="px-3 py-1 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 rounded transition-colors disabled:opacity-50"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleSubmit}
                            disabled={isLoading}
                            className="px-3 py-1 text-xs font-medium bg-primary text-on-primary rounded hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-1"
                        >
                            {isLoading ? <Loader size={12} className="animate-spin" /> : null}
                            Submit
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
