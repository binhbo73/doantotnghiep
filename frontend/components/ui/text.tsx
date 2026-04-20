// components/ui/text.tsx - Typography components for consistent text styling
import { ReactNode, HTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

// Display
interface DisplayProps extends HTMLAttributes<HTMLHeadingElement> {
    level?: 'xl' | 'lg' | 'base'
    children: ReactNode
}

export const Display = ({ level = 'base', className, children, ...props }: DisplayProps) => {
    const displayMap = {
        xl: 'font-[family:var(--font-serif)] text-[72px] font-normal leading-none tracking-[-1.584px]',
        lg: 'font-[family:var(--font-serif)] text-[64px] font-normal leading-none tracking-[-1.408px]',
        base: 'font-[family:var(--font-serif)] text-[48px] font-normal leading-none tracking-[-1.056px]',
    }
    return (
        <h1 className={cn(displayMap[level], className)} {...props}>
            {children}
        </h1>
    )
}

// Heading
interface HeadingProps extends HTMLAttributes<HTMLHeadingElement> {
    level?: 1 | 2 | 3
    children: ReactNode
}

export const Heading = ({ level = 1, className, children, ...props }: HeadingProps) => {
    const headingMap = {
        1: 'font-[family:var(--font-serif)] text-[32px] font-normal leading-[1.13] tracking-[-0.704px]',
        2: 'font-[family:var(--font-serif)] text-[24px] font-normal leading-[1.33] tracking-[-0.288px]',
        3: 'font-[family:var(--font-serif)] text-[20px] font-normal leading-[1.33] tracking-[-0.24px]',
    }
    const Tag = `h${level}` as const
    return (
        <Tag className={cn(headingMap[level], className)} {...props}>
            {children}
        </Tag>
    )
}

// Body
interface BodyProps extends HTMLAttributes<HTMLParagraphElement> {
    variant?: 'lg' | 'emphasis' | 'base' | 'medium' | 'semibold'
    children: ReactNode
}

export const Body = ({ variant = 'base', className, children, ...props }: BodyProps) => {
    const variantMap = {
        lg: 'font-sans text-[18px] font-normal leading-[1.6] tracking-[-0.165px]',
        emphasis: 'font-sans text-[17px] font-semibold leading-[1.6]',
        base: 'font-sans text-[16px] font-normal leading-[1.5]',
        medium: 'font-sans text-[16px] font-medium leading-[1.5]',
        semibold: 'font-sans text-[16px] font-semibold leading-[1.5]',
    }
    return (
        <p className={cn(variantMap[variant], className)} {...props}>
            {children}
        </p>
    )
}

// Small
interface SmallProps extends HTMLAttributes<HTMLElement> {
    variant?: 'base' | 'medium' | 'semibold' | 'light'
    children: ReactNode
}

export const Small = ({ variant = 'base', className, children, ...props }: SmallProps) => {
    const variantMap = {
        base: 'font-sans text-[15px] font-normal leading-[1.6] tracking-[-0.165px]',
        medium: 'font-sans text-[15px] font-medium leading-[1.6] tracking-[-0.165px]',
        semibold: 'font-sans text-[15px] font-semibold leading-[1.6] tracking-[-0.165px]',
        light: 'font-sans text-[15px] font-light leading-[1.47] tracking-[-0.165px]',
    }
    return (
        <small className={cn(variantMap[variant], className)} {...props}>
            {children}
        </small>
    )
}

// Caption
interface CaptionProps extends HTMLAttributes<HTMLElement> {
    variant?: 'lg' | 'base'
    children: ReactNode
}

export const Caption = ({ variant = 'base', className, children, ...props }: CaptionProps) => {
    const variantMap = {
        lg: 'font-sans text-[14px] font-medium leading-[1.5] tracking-[-0.182px]',
        base: 'font-sans text-[13px] font-normal leading-[1.5] tracking-[-0.13px]',
    }
    return (
        <span className={cn(variantMap[variant], className)} {...props}>
            {children}
        </span>
    )
}

// Label
interface LabelProps extends HTMLAttributes<HTMLLabelElement> {
    children: ReactNode
}

export const Label = ({ className, children, ...props }: LabelProps) => (
    <label className={cn('font-sans text-[12px] font-medium leading-[1.4]', className)} {...props}>
        {children}
    </label>
)

// Monospace
interface MonoProps extends HTMLAttributes<HTMLElement> {
    variant?: 'body' | 'caption' | 'label'
    children: ReactNode
}

export const Mono = ({ variant = 'body', className, children, ...props }: MonoProps) => {
    const variantMap = {
        body: 'font-mono text-[14px] font-normal leading-[1.5]',
        caption: 'font-mono text-[13px] font-normal leading-[1.5]',
        label: 'font-mono text-[12px] font-normal leading-[1.4]',
    }
    return (
        <code className={cn(variantMap[variant], className)} {...props}>
            {children}
        </code>
    )
}
