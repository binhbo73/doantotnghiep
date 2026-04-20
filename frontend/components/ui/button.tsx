// components/ui/button.tsx - Button component following Linear design
import { ReactNode, ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    /**
     * Button variant following Linear design system
     * - ghost: Default transparent button (rgba 0.02-0.05 bg)
     * - primary: Sky blue CTA (#0284c7)
     * - icon: Circular icon button (50% radius)
     * - subtle: Very light background (rgba 0.04)
     * - danger: Red background for destructive actions
     */
    variant?: 'ghost' | 'primary' | 'icon' | 'subtle' | 'danger'

    /**
     * Button size
     * - sm: 12px label, compact padding
     * - md: 14px label, standard padding (default)
     * - lg: 16px label, relaxed padding
     */
    size?: 'sm' | 'md' | 'lg'

    /**
     * Button content
     */
    children: ReactNode
}

/**
 * Button Component - Base interactive element
 *
 * Design: Linear-inspired with multiple variants
 * - Ghost: Default transparent button with subtle border
 * - Primary: Sky blue for main CTAs
 * - Icon: For icon-only buttons, circular shape
 * - Subtle: Very light transparent background
 * - Danger: Red for destructive actions
 *
 * @example
 * // Primary CTA button
 * <Button variant="primary" size="lg">Start Building</Button>
 *
 * // Ghost button (default)
 * <Button>Cancel</Button>
 *
 * // Icon button
 * <Button variant="icon" size="sm" aria-label="Close">✕</Button>
 *
 * // Danger button
 * <Button variant="danger">Delete Document</Button>
 */
export const Button = ({
    variant = 'ghost',
    size = 'md',
    children,
    className,
    disabled,
    ...props
}: ButtonProps) => {
    const baseClasses = cn(
        // Base: Font & transition
        'font-inter font-semibold transition-all duration-200',
        'cursor-pointer rounded-xl',
        'focus-visible:outline-none focus-visible:shadow-[0_0_0_4px_rgba(125,140,124,0.18)]',
        'disabled:opacity-50 disabled:cursor-not-allowed',

        // Size variations
        size === 'sm' && 'text-[12px] px-3 py-1.5 h-7',
        size === 'md' && 'text-[14px] px-4 py-2 h-9',
        size === 'lg' && 'text-[16px] px-6 py-3 h-11',

        // Variant styles
        variant === 'ghost' && [
            'bg-transparent',
            'border border-solid border-border',
            'text-foreground',
            'hover:bg-muted hover:border-[#d8d3c8]',
        ],
        variant === 'primary' && [
            'bg-sky-600',
            'text-white',
            'border border-solid border-sky-600',
            'hover:bg-sky-700 hover:border-sky-700',
        ],
        variant === 'subtle' && [
            'bg-muted',
            'border border-solid border-border',
            'text-foreground',
            'hover:bg-secondary',
        ],
        variant === 'danger' && [
            'bg-destructive',
            'text-white',
            'border border-solid border-destructive',
            'hover:bg-[#dc2626]',
        ],
        variant === 'icon' && [
            'bg-muted',
            'border border-solid border-border',
            'text-foreground',
            'rounded-full w-9 h-9 p-0 flex items-center justify-center',
            'hover:bg-secondary',
        ],

        className
    )

    return (
        <button
            className={baseClasses}
            disabled={disabled}
            {...props}
        >
            {children}
        </button>
    )
}

export default Button
