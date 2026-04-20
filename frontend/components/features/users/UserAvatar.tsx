'use client'

/**
 * User Avatar Component
 * Displays user profile picture with initial fallback
 */

import React, { useState } from 'react'
import { User } from 'lucide-react'

interface UserAvatarProps {
    src?: string | null
    alt: string
    initials?: string
    size?: 'sm' | 'md' | 'lg'
    className?: string
}

const SIZE_MAP = {
    sm: { size: 32, textSize: 'text-xs' },
    md: { size: 40, textSize: 'text-sm' },
    lg: { size: 48, textSize: 'text-base' },
}

export function UserAvatar({ src, alt, initials, size = 'md', className = '' }: UserAvatarProps) {
    const [imageError, setImageError] = useState(!src)
    const sizeConfig = SIZE_MAP[size]

    if (imageError || !src) {
        return (
            <div
                className={`flex items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-blue-600 text-white ${sizeConfig.textSize} font-semibold ${className}`}
                style={{
                    width: sizeConfig.size,
                    height: sizeConfig.size,
                }}
            >
                {initials ? (
                    <span>{initials}</span>
                ) : (
                    <User size={sizeConfig.size / 2} />
                )}
            </div>
        )
    }

    return (
        <img
            src={src}
            alt={alt}
            onError={() => setImageError(true)}
            className={`rounded-full object-cover ${className}`}
            style={{
                width: sizeConfig.size,
                height: sizeConfig.size,
            }}
        />
    )
}

export default UserAvatar
