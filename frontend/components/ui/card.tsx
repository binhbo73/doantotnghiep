// components/ui/card.tsx - Card component for content containers
import { ReactNode, HTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
    /**
     * Card elevation level
     * - subtle: Minimal elevation, almost flat
     * - base: Standard elevation (default)
     * - elevated: Prominent elevation
     */
    elevation?: 'subtle' | 'base' | 'elevated'

    /**
     * Card padding
     * - none: No padding
     * - sm: 12px padding
     * - md: 16px padding (default)
     * - lg: 24px padding
     */
    padding?: 'none' | 'sm' | 'md' | 'lg'

    children: ReactNode
}

/**
 * Card Component - Container for content
 *
 * Design: Linear-inspired dark card with translucent background
 * Uses rgba(255,255,255, 0.02-0.05) for background (never solid)
 * Semi-transparent white border for structure
 *
 * @example
 * // Standard card
 * <Card>
 *   <h3>Document</h3>
 *   <p>Description</p>
 * </Card>
 *
 * // Elevated card with custom padding
 * <Card elevation="elevated" padding="lg">
 *   Content here
 * </Card>
 */
export const Card = ({
    elevation = 'base',
    padding = 'md',
    children,
    className,
    ...props
}: CardProps) => {
    const baseClasses = cn(
        // Base styling
        'rounded-2xl',
        'transition-all duration-200',

        // Elevation (background opacity)
        elevation === 'subtle' && [
            'bg-muted/50',
            'border border-solid border-border',
            'hover:bg-muted',
        ],
        elevation === 'base' && [
            'bg-card',
            'border border-solid border-border',
            'hover:bg-[#fffdfa]',
        ],
        elevation === 'elevated' && [
            'bg-card',
            'border border-solid border-border',
            'hover:bg-[#fffdfa]',
            'shadow-[0_18px_45px_rgba(92,83,70,0.08)]',
        ],

        // Padding
        padding === 'none' && 'p-0',
        padding === 'sm' && 'p-[12px]',
        padding === 'md' && 'p-[16px]',
        padding === 'lg' && 'p-[24px]',

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

export default Card
