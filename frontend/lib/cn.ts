// lib/cn.ts - Class name utility with type safety
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merge Tailwind and custom classes with proper override handling
 * Usage: cn('px-4 py-2', 'px-8') => 'px-8 py-2'
 */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

/**
 * Design system color utilities for inline styling
 */
export const dsColors = {
    // Backgrounds
    bg: {
        marketing: 'background-color: #08090a',
        panel: 'background-color: #0f1011',
        level3: 'background-color: #191a1b',
        secondary: 'background-color: #28282c',
    },

    // Text
    text: {
        primary: 'color: #f7f8f8',
        secondary: 'color: #d0d6e0',
        tertiary: 'color: #8a8f98',
        quaternary: 'color: #62666d',
    },

    // Brand
    brandIndigo: '#5e6ad2',
    accentViolet: '#7170ff',
    successEmerald: '#10b981',
    errorRed: '#ef4444',
}

/**
 * Responsive breakpoint utilities
 */
export const breakpoints = {
    mobileSmall: 600,
    mobile: 640,
    tablet: 768,
    desktopSmall: 1024,
    desktop: 1280,
} as const

export function isMobile(width: number): boolean {
    return width < breakpoints.tablet
}

export function isTablet(width: number): boolean {
    return width >= breakpoints.tablet && width < breakpoints.desktop
}

export function isDesktop(width: number): boolean {
    return width >= breakpoints.desktop
}
