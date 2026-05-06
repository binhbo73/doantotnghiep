'use client'

import React from 'react'

interface SkeletonLoaderProps {
    lines?: number
    height?: string
    width?: string
    className?: string
}

/**
 * Skeleton Loader Component
 * Shows loading state while checking permissions
 */
export function SkeletonLoader({
    lines = 3,
    height = 'h-4',
    width = 'w-full',
    className = '',
}: SkeletonLoaderProps) {
    return (
        <div className={`space-y-2 ${className}`}>
            {Array.from({ length: lines }).map((_, i) => (
                <div
                    key={i}
                    className={`${height} ${width} rounded-lg animate-pulse`}
                    style={{
                        backgroundColor: '#e5e7eb',
                    }}
                />
            ))}
        </div>
    )
}

/**
 * Spinner Component
 * Loading indicator
 */
export function Spinner() {
    return (
        <div className="flex items-center justify-center">
            <div
                className="w-6 h-6 rounded-full animate-spin"
                style={{
                    backgroundColor: 'transparent',
                    borderColor: '#0058be',
                    borderWidth: '2px',
                    borderTopColor: 'transparent',
                }}
            />
        </div>
    )
}

export default SkeletonLoader
