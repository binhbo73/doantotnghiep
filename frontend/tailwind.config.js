/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './app/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
        './styles/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                // Backgrounds
                'bg-marketing': '#08090a',
                'bg-panel': '#1a1b1f',
                'bg-surface': '#252a33',
                'bg-elevated': '#191a1b',
                // Text
                'text-primary': '#f7f8f8',
                'text-secondary': '#d0d6e0',
                'text-muted': '#8a8f98',
                'text-disabled': '#62666d',
                // Brand
                'brand': '#5e6ad2',
                'brand-hover': '#828fff',
                'accent': '#7170ff',
                // Status
                'success': '#10b981',
                'error': '#ef4444',
                // Borders
                'border-light': 'rgba(255, 255, 255, 0.1)',
                'border-subtle': 'rgba(255, 255, 255, 0.05)',
            },
            fontFamily: {
                inter: ['Inter', 'system-ui', 'sans-serif'],
                mono: ['Berkeley Mono', 'monospace'],
            },
            fontWeight: {
                light: 300,
                normal: 400,
                medium: 500,
                semibold: 600,
                bold: 700,
            },
            letterSpacing: {
                tighter: '-1.584px',
                tight: '-1.408px',
                tight2: '-1.056px',
                tight3: '-0.704px',
                tight4: '-0.288px',
                tight5: '-0.24px',
                tight6: '-0.165px',
                tight7: '-0.13px',
                normal: '0px',
            },
            spacing: {
                micro: '2px',
                xs: '4px',
                sm: '8px',
                md: '12px',
                lg: '16px',
                xl: '24px',
                '2xl': '32px',
                '3xl': '48px',
            },
            borderRadius: {
                micro: '2px',
                xs: '4px',
                sm: '6px',
                md: '8px',
                lg: '12px',
                xl: '16px',
            },
            boxShadow: {
                subtle: 'rgba(0, 0, 0, 0.03) 0px 1.2px 0px',
                focus: 'rgba(0, 0, 0, 0.1) 0px 4px 12px',
                elevated: 'rgba(0, 0, 0, 0.4) 0px 2px 4px',
                inset: 'rgba(0, 0, 0, 0.2) 0px 0px 12px 0px inset',
            },
        },
    },
    plugins: [],
}
