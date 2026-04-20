// config/design-tokens.ts - Design tokens for use in code
export const designTokens = {
    // Typography
    typography: {
        fontFamily: {
            inter:
                "'Inter', -apple-system, system-ui, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif",
            mono: "'Berkeley Mono', ui-monospace, 'SF Mono', Menlo, 'Courier New', monospace",
        },
        fontFeatures: {
            inter: '"cv01", "ss03"',
        },
    },

    // Colors
    colors: {
        // Backgrounds
        background: {
            marketing: '#08090a',
            panel: '#0f1011',
            level3: '#191a1b',
            secondary: '#28282c',
        },

        // Text
        text: {
            primary: '#f7f8f8',
            secondary: '#d0d6e0',
            tertiary: '#8a8f98',
            quaternary: '#62666d',
        },

        // Brand & Accent
        brand: {
            indigo: '#5e6ad2',
            violet: '#7170ff',
            hover: '#828fff',
            lavender: '#7a7fad',
        },

        // Status
        status: {
            success: '#27a644',
            emerald: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6',
        },

        // Borders
        border: {
            primary: '#23252a',
            secondary: '#34343a',
            tertiary: '#3e3e44',
            subtle: 'rgba(255, 255, 255, 0.05)',
            standard: 'rgba(255, 255, 255, 0.08)',
        },

        // Light Mode
        light: {
            bg: '#f7f8f8',
            surface: '#f3f4f5',
            border: '#d0d6e0',
            borderAlt: '#e6e6e6',
            white: '#ffffff',
        },

        // Overlay
        overlay: 'rgba(0, 0, 0, 0.85)',
    },

    // Shadows
    shadows: {
        subtle: 'rgba(0, 0, 0, 0.03) 0px 1.2px 0px',
        focus: 'rgba(0, 0, 0, 0.1) 0px 4px 12px',
        elevated: 'rgba(0, 0, 0, 0.4) 0px 2px 4px',
        inset: 'rgba(0, 0, 0, 0.2) 0px 0px 12px 0px inset',
        ring: 'rgba(0, 0, 0, 0.2) 0px 0px 0px 1px',
        dialog:
            'rgba(0, 0, 0, 0) 0px 8px 2px, rgba(0, 0, 0, 0.01) 0px 5px 2px, rgba(0, 0, 0, 0.04) 0px 3px 2px, rgba(0, 0, 0, 0.07) 0px 1px 1px, rgba(0, 0, 0, 0.08) 0px 0px 1px',
    },

    // Spacing
    spacing: {
        xs: '4px',
        sm: '8px',
        md: '12px',
        lg: '16px',
        xl: '24px',
        '2xl': '32px',
        '3xl': '48px',
        '4xl': '64px',
    },

    // Border Radius
    radius: {
        micro: '2px',
        xs: '4px',
        sm: '6px',
        md: '8px',
        lg: '12px',
        xl: '22px',
        pill: '9999px',
        circle: '50%',
    },

    // Transitions
    transitions: {
        fast: '150ms cubic-bezier(0.4, 0, 0.2, 1)',
        base: '200ms cubic-bezier(0.4, 0, 0.2, 1)',
        slow: '300ms cubic-bezier(0.4, 0, 0.2, 1)',
    },
} as const

export type DesignTokens = typeof designTokens
