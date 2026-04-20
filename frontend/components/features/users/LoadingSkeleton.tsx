'use client'

/**
 * Loading Skeleton Component
 * Displays skeleton loaders for user table
 */

import React from 'react'

interface LoadingSkeletonProps {
    rows?: number
}

export function LoadingSkeleton({ rows = 5 }: LoadingSkeletonProps) {
    return (
        <div className="space-y-3">
            {Array.from({ length: rows }).map((_, i) => (
                <div
                    key={i}
                    className="h-16 rounded-lg bg-gradient-to-r from-gray-200 to-gray-100 animate-pulse"
                />
            ))}
        </div>
    )
}

export default LoadingSkeleton
