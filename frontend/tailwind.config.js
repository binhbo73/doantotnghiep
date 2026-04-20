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
                // Backgrounds (Dark theme - legacy)
                'bg-marketing': '#08090a',
                'bg-panel': '#1a1b1f',
                'bg-surface': '#252a33',
                'bg-elevated': '#191a1b',
                // Text (Dark theme - legacy)
                'text-primary': '#f7f8f8',
                'text-secondary': '#d0d6e0',
                'text-muted': '#8a8f98',
                'text-disabled': '#62666d',
                // Brand (Dark theme - legacy)
                'brand': '#5e6ad2',
                'brand-hover': '#828fff',
                'accent': '#7170ff',
                // Status (Dark theme - legacy)
                'success': '#10b981',
                'error': '#ef4444',
                // Borders (Dark theme - legacy)
                'border-light': 'rgba(255, 255, 255, 0.1)',
                'border-subtle': 'rgba(255, 255, 255, 0.05)',

                // Stitch Design System - Light theme
                'surface': '#f9f9ff',
                'surface_bright': '#f9f9ff',
                'surface_container': '#e7eefe',
                'surface_container_high': '#e2e8f8',
                'surface_container_highest': '#dce2f3',
                'surface_container_low': '#f0f3ff',
                'surface_container_lowest': '#ffffff',
                'surface_dim': '#d3daea',
                'surface_variant': '#dce2f3',
                'surface_tint': '#005ac2',

                'primary': '#0058be',
                'primary_container': '#2170e4',
                'primary_fixed': '#d8e2ff',
                'primary_fixed_dim': '#adc6ff',

                'secondary': '#495e8a',
                'secondary_container': '#b6ccff',
                'secondary_fixed': '#d8e2ff',
                'secondary_fixed_dim': '#b1c6f9',

                'tertiary': '#924700',
                'tertiary_container': '#b75b00',
                'tertiary_fixed': '#ffdcc6',
                'tertiary_fixed_dim': '#ffb786',

                'error': '#ba1a1a',
                'error_container': '#ffdad6',

                'on_surface': '#151c27',
                'on_surface_variant': '#424754',
                'on_primary': '#ffffff',
                'on_primary_container': '#fefcff',
                'on_primary_fixed': '#001a42',
                'on_primary_fixed_variant': '#004395',
                'on_secondary': '#ffffff',
                'on_secondary_container': '#405682',
                'on_secondary_fixed': '#001a42',
                'on_secondary_fixed_variant': '#304671',
                'on_tertiary': '#ffffff',
                'on_tertiary_container': '#fffbff',
                'on_tertiary_fixed': '#311400',
                'on_tertiary_fixed_variant': '#723600',
                'on_error': '#ffffff',
                'on_error_container': '#93000a',

                'outline': '#727785',
                'outline_variant': '#c2c6d6',
                'inverse_surface': '#2a313d',
                'inverse_on_surface': '#ebf1ff',
                'inverse_primary': '#adc6ff',

                'background': '#f9f9ff',
                'on_background': '#151c27',
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
