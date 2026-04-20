'use client'

import React from 'react'

interface ActivityItem {
    id: string
    title: string
    description: string
    time: string
    avatarChar: string
    avatarBgColor?: string
    category?: string
}

interface RecentActivityCardProps {
    activities: ActivityItem[]
    onViewAll?: () => void
}

export function RecentActivityCard({ activities, onViewAll }: RecentActivityCardProps) {
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
                <button
                    onClick={onViewAll}
                    className="text-xs font-medium hover:underline"
                    style={{ color: '#0058be' }}
                >
                    Xem tất cả
                </button>
            </div>

            {/* Activity Items */}
            <div className="space-y-2">
                {activities.map((activity) => (
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
                                    {activity.title}
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
                ))}
            </div>
        </div>
    )
}
