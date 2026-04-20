// components/features/UserAvatar.tsx - User avatar with role badge
import { Badge } from '@/components/ui/badge'
import { HTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

interface UserAvatarProps extends HTMLAttributes<HTMLDivElement> {
    /**
     * User initials or username
     */
    initial: string

    /**
     * User's role
     */
    role?: 'admin' | 'editor' | 'viewer'

    /**
     * Avatar size
     */
    size?: 'sm' | 'md' | 'lg'
}

/**
 * UserAvatar - Display user avatar with role indicator
 *
 * Design: Linear-inspired user profile indicator
 * - Circular avatar with initial
 * - Role badge attached to bottom-right
 * - Size variations: 24px (sm), 32px (md), 40px (lg)
 *
 * @example
 * <UserAvatar initial="JD" role="admin" size="md" />
 */
export const UserAvatar = ({ initial, role, size = 'md', className, ...props }: UserAvatarProps) => {
    const sizeConfig = {
        sm: { container: 'w-6 h-6 text-[10px]', badge: 'text-[8px]' },
        md: { container: 'w-8 h-8 text-[12px]', badge: 'text-[10px]' },
        lg: { container: 'w-10 h-10 text-[14px]', badge: 'text-[11px]' },
    }

    const roleConfig = {
        admin: { color: 'error' as const, label: 'Admin' },
        editor: { color: 'primary' as const, label: 'Editor' },
        viewer: { color: 'subtle' as const, label: 'Viewer' },
    }

    const config = roleConfig[role || 'viewer']

    return (
        <div className="relative inline-block" {...props}>
            <div
                className={cn(
                    'flex items-center justify-center rounded-full',
                    'bg-primary text-primary-foreground border border-primary',
                    'font-medium font-inter',
                    sizeConfig[size].container,
                    className
                )}
            >
                {initial.toUpperCase()}
            </div>

            {/* Role badge */}
            {role && (
                <Badge
                    variant={config.color}
                    size="sm"
                    shape="rounded"
                    className={cn(
                        'absolute -bottom-1 -right-1 px-1 py-0.5',
                        sizeConfig[size].badge
                    )}
                >
                    {config.label[0]}
                </Badge>
            )}
        </div>
    )
}

export default UserAvatar
