'use client'

/**
 * useFeedback Hook - Manage message feedback (upvote/downvote)
 * 
 * Features:
 * - Submit feedback on AI messages
 * - Fetch feedback for a message with stats
 * - Delete own feedback
 * - Track loading and error states
 * - Optimistic UI updates
 */



import { useState, useCallback } from 'react'
import { chatService, type Feedback, type FeedbackRequest, type FeedbackStats } from '@/services/chat'
import { useToast } from './useToast'

interface UseFeedbackReturn {
    // State
    feedbacks: Map<string, Feedback[]>
    feedbackStats: Map<string, FeedbackStats>
    userFeedback: Map<string, 'upvote' | 'downvote'>
    loading: Map<string, boolean>
    error: Map<string, string | null>

    // Methods
    submitFeedback: (messageId: string, rating: 'upvote' | 'downvote', comment?: string) => Promise<void>
    getFeedback: (messageId: string) => Promise<void>
    deleteFeedback: (messageId: string) => Promise<void>
    hasUserFeedback: (messageId: string) => boolean
    getUserFeedback: (messageId: string) => 'upvote' | 'downvote' | null
    getFeedbackStats: (messageId: string) => FeedbackStats | null
}

export function useFeedback(): UseFeedbackReturn {
    const [feedbacks, setFeedbacks] = useState<Map<string, Feedback[]>>(new Map())
    const [feedbackStats, setFeedbackStats] = useState<Map<string, FeedbackStats>>(new Map())
    const [userFeedback, setUserFeedback] = useState<Map<string, 'upvote' | 'downvote'>>(new Map())
    const [loading, setLoading] = useState<Map<string, boolean>>(new Map())
    const [error, setError] = useState<Map<string, string | null>>(new Map())
    const { toast } = useToast()

    const submitFeedback = useCallback(
        async (messageId: string, rating: 'upvote' | 'downvote', comment?: string) => {
            try {
                // Set loading state
                setLoading((prev) => new Map(prev).set(messageId, true))
                setError((prev) => new Map(prev).set(messageId, null))

                // Optimistic UI update
                setUserFeedback((prev) => new Map(prev).set(messageId, rating))

                // Submit feedback
                const feedback = await chatService.submitFeedback(messageId, {
                    rating,
                    comment: comment?.trim() || undefined,
                })

                // Update feedback list and stats
                setFeedbacks((prev) => {
                    const newMap = new Map(prev)
                    const existing = newMap.get(messageId) || []
                    const filtered = existing.filter((f) => f.account_id !== feedback.account_id)
                    newMap.set(messageId, [...filtered, feedback])
                    return newMap
                })

                // Success toast
                const ratingText = rating === 'upvote' ? 'thumbs up' : 'thumbs down'
                toast({
                    title: 'Feedback submitted',
                    description: `Thank you for your ${ratingText}!`,
                    type: 'success',
                })
            } catch (err) {
                const errorMessage = err instanceof Error ? err.message : 'Failed to submit feedback'
                setError((prev) => new Map(prev).set(messageId, errorMessage))
                setUserFeedback((prev) => {
                    const newMap = new Map(prev)
                    newMap.delete(messageId)
                    return newMap
                })
                toast({
                    title: 'Error',
                    description: errorMessage,
                    type: 'error',
                })
            } finally {
                setLoading((prev) => new Map(prev).set(messageId, false))
            }
        },
        [toast]
    )

    const getFeedback = useCallback(async (messageId: string) => {
        try {
            setLoading((prev) => new Map(prev).set(messageId, true))
            setError((prev) => new Map(prev).set(messageId, null))

            const response = await chatService.getFeedback(messageId)
            setFeedbacks((prev) => new Map(prev).set(messageId, response.feedbacks))
            setFeedbackStats((prev) => new Map(prev).set(messageId, response.stats))
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to fetch feedback'
            setError((prev) => new Map(prev).set(messageId, errorMessage))
        } finally {
            setLoading((prev) => new Map(prev).set(messageId, false))
        }
    }, [])

    const deleteFeedback = useCallback(
        async (messageId: string) => {
            try {
                setLoading((prev) => new Map(prev).set(messageId, true))
                setError((prev) => new Map(prev).set(messageId, null))

                await chatService.deleteFeedback(messageId)

                // Clear from state
                setUserFeedback((prev) => {
                    const newMap = new Map(prev)
                    newMap.delete(messageId)
                    return newMap
                })

                toast({
                    title: 'Feedback deleted',
                    description: 'Your feedback has been removed',
                    type: 'success',
                })
            } catch (err) {
                const errorMessage = err instanceof Error ? err.message : 'Failed to delete feedback'
                setError((prev) => new Map(prev).set(messageId, errorMessage))
                toast({
                    title: 'Error',
                    description: errorMessage,
                    type: 'error',
                })
            } finally {
                setLoading((prev) => new Map(prev).set(messageId, false))
            }
        },
        [toast]
    )

    const hasUserFeedback = useCallback((messageId: string) => {
        return userFeedback.has(messageId)
    }, [userFeedback])

    const getUserFeedback = useCallback(
        (messageId: string) => {
            return userFeedback.get(messageId) || null
        },
        [userFeedback]
    )

    const getFeedbackStats = useCallback(
        (messageId: string) => {
            return feedbackStats.get(messageId) || null
        },
        [feedbackStats]
    )

    return {
        feedbacks,
        feedbackStats,
        userFeedback,
        loading,
        error,
        submitFeedback,
        getFeedback,
        deleteFeedback,
        hasUserFeedback,
        getUserFeedback,
        getFeedbackStats,
    }
}
