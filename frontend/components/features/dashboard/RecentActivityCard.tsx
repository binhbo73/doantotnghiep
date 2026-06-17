'use client'

import React, { useEffect, useState } from 'react'
import { getRecentActivities } from '@/services/audit'
import { ApiError } from '@/services/api'
import type { ActivityItem } from '@/services/audit'

interface RecentActivityCardProps {
    activities?: ActivityItem[]
    onViewAll?: () => void
}

function formatActivityTitle(title: string) {
    return title.replace(
        /\s*\([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\)\s*$/i,
        ''
    )
}

export function RecentActivityCard({ activities: initialActivities, onViewAll }: RecentActivityCardProps) {
    const [activities, setActivities] = useState<ActivityItem[]>(initialActivities || [])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        // If activities are passed as prop, use them
        if (initialActivities && initialActivities.length > 0) {
            setActivities(initialActivities)
            setLoading(false)
            return
        }

        // Otherwise, fetch from API
        fetchRecentActivities()
    }, [initialActivities])

    const fetchRecentActivities = async () => {
        try {
            setLoading(true)
            setError(null)

            // Build the same query for debugging visibility
            const qp = new URLSearchParams()
            qp.append('limit', String(10))
            const endpoint = `/audit-logs/recent-activity?${qp.toString()}`
            console.debug('Fetching recent activities from:', endpoint)

            const response = await getRecentActivities({ limit: 10 })

            if (response && response.success && response.data?.items) {
                setActivities(response.data.items)
            } else {
                setError('Failed to load recent activities')
            }
        } catch (err) {
            // If backend returns 404, treat as empty (no activities available)
            if (err instanceof ApiError && err.statusCode === 404) {
                setActivities([])
                setError(null)
                console.info('Recent activities endpoint not found (404). Showing empty state.')
            } else {
                setError('Error loading recent activities')
                console.error('Error fetching activities:', err)
            }
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return (
            <div className="space-y-2">
                <div className="flex items-center justify-between mb-3">
                    <h2
                        className="text-sm font-bold"
                        style={{ color: '#151c27' }}
                    >
                        Hoạt động gần đây
                    </h2>
                </div>
                <div className="text-center py-8">
                    <p style={{ color: '#727785' }}>Đang tải...</p>
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="space-y-2">
                <div className="flex items-center justify-between mb-3">
                    <h2
                        className="text-sm font-bold"
                        style={{ color: '#151c27' }}
                    >
                        Hoạt động gần đây
                    </h2>
                </div>
                <div className="text-center py-8">
                    <p style={{ color: '#f5222d' }}>{error}</p>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-2">
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
                <h2
                    className="text-sm font-bold"
                    style={{ color: '#151c27' }}
                >
                    Hoạt động gần đây
                </h2>
                {/* <button
                    onClick={onViewAll}
                    className="text-xs font-medium hover:underline"
                    style={{ color: '#0058be' }}
                >
                    Xem tất cả
                </button> */}
            </div>

            {/* Activity Items */}
            <div className="space-y-2">
                {activities && activities.length > 0 ? (
                    activities.map((activity) => (
                        <div
                            key={activity.id}
                            className="flex gap-2 p-2 rounded-lg transition-all hover:bg-surface_container_low"
                            style={{
                                backgroundColor: '#f9f9ff',
                                border: '1px solid #e7eefe',
                            }}
                        >
                            {/* Avatar */}
                            <div
                                className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 font-bold text-white text-sm"
                                style={{
                                    backgroundColor: activity.avatarBgColor || '#0058be',
                                }}
                            >
                                {activity.avatarChar}
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                                <div className="flex items-start justify-between gap-2 mb-0.5">
                                    <h3
                                        className="text-xs font-bold"
                                        style={{ color: '#151c27' }}
                                    >
                                        {formatActivityTitle(activity.title)}
                                    </h3>
                                    <span
                                        className="text-xs font-medium flex-shrink-0"
                                        style={{ color: '#727785' }}
                                    >
                                        {activity.time}
                                    </span>
                                </div>
                                <p
                                    className="text-xs mb-1"
                                    style={{ color: '#727785' }}
                                >
                                    {activity.description}
                                </p>
                                {activity.category && (
                                    <span
                                        className="inline-block text-xs font-medium px-1.5 py-0.5 rounded-full"
                                        style={{
                                            backgroundColor: '#e7eefe',
                                            color: '#0058be',
                                        }}
                                    >
                                        {activity.category}
                                    </span>
                                )}
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="text-center py-8">
                        <p style={{ color: '#727785' }}>Chưa có hoạt động nào</p>
                    </div>
                )}
            </div>
        </div>
    )
}
