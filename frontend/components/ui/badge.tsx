// components/ui/badge.tsx - Badge and pill components
import { ReactNode, HTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
    /**
     * Badge variant
     * - neutral: Transparent with border (default)
     * - success: Green emerald background
     * - error: Red background
     * - warning: Orange background
     * - info: Blue background
     * - primary: Brand indigo background
     * - subtle: Very light transparent background
     */
    variant?:
    | 'neutral'
    | 'success'
    | 'error'
    | 'warning'
    | 'info'
    | 'primary'
    | 'subtle'

    /**
     * Badge size
     * - sm: 10px, compact
     * - md: 12px, standard (default)
     * - lg: 14px, relaxed
     */
    size?: 'sm' | 'md' | 'lg'

    /**
     * Badge shape
     * - pill: 9999px radius (default, for tags)
     * - rounded: 6px radius (for inline badges)
     */
    shape?: 'pill' | 'rounded'

    children: ReactNode
}

/**
 * Badge Component - Status and categorical indicator
 *
 * Design: Linear-inspired badge system
 * Neutral pill for tags/filters
 * Color pills for status indication
 *
 * @example
 * // Neutral pill badge
 * <Badge variant="neutral" shape="pill">Filter Tag</Badge>
 *
 * // Status badge
 * <Badge variant="success" size="sm">Accessible</Badge>
 *
 * // Inline badge
 * <Badge variant="primary" shape="rounded">New</Badge>
 */
export const Badge = ({
    variant = 'neutral',
    size = 'md',
    shape = 'pill',
    children,
    className,
    ...props
}: BadgeProps) => {
    const baseClasses = cn(
        // Base
        'font-inter font-medium inline-flex items-center gap-1',
        'whitespace-nowrap transition-colors duration-200',

        // Size
        size === 'sm' && 'text-[10px] px-2 py-0.5',
        size === 'md' && 'text-[12px] px-2.5 py-1',
        size === 'lg' && 'text-[14px] px-3 py-1.5',

        // Shape
        shape === 'pill' && 'rounded-full',
        shape === 'rounded' && 'rounded-md',

        // Variants
        variant === 'neutral' && [
            'bg-muted',
            'border border-solid border-border',
            'text-muted-foreground',
        ],
        variant === 'success' && [
            'bg-primary',
            'border border-solid border-primary',
            'text-primary-foreground',
        ],
        variant === 'error' && [
            'bg-[#ef4444]',
            'border border-solid border-[#ef4444]',
            'text-white',
        ],
        variant === 'warning' && [
            'bg-accent',
            'border border-solid border-accent',
            'text-accent-foreground',
        ],
        variant === 'info' && [
            'bg-secondary',
            'border border-solid border-border',
            'text-foreground',
        ],
        variant === 'primary' && [
            'bg-primary',
            'border border-solid border-primary',
            'text-primary-foreground',
        ],
        variant === 'subtle' && [
            'bg-[#f0eadf]',
            'border border-solid border-border',
            'text-foreground',
        ],

        className
    )

    return (
        <div
            className={baseClasses}
            {...props}
        >
            {children}
        </div>
    )
}

export default Badge
