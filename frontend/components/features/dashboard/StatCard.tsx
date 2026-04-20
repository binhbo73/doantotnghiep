'use client'

interface StatCardProps {
    icon: React.ReactNode
    label: string
    value: string | number
    trend?: 'up' | 'down' | 'neutral'
    trendPercent?: number
    iconBgColor?: string
}

export function StatCard({
    icon,
    label,
    value,
    trend = 'neutral',
    trendPercent = 0,
    iconBgColor = '#f0f3ff',
}: StatCardProps) {
    const getTrendColor = () => {
        if (trend === 'up') return '#10b981'
        if (trend === 'down') return '#ef4444'
        return '#727785'
    }

    const getTrendSymbol = () => {
        if (trend === 'up') return '↑'
        if (trend === 'down') return '↓'
        return ''
    }

    return (
        <div
            className="rounded-lg p-3 transition-all hover:shadow-lg"
            style={{
                backgroundColor: '#ffffff',
                border: '1px solid #dce2f3',
            }}
        >
            {/* Icon Container */}
            <div
                className="w-10 h-10 rounded-lg flex items-center justify-center mb-2 text-lg"
                style={{ backgroundColor: iconBgColor }}
            >
                {icon}
            </div>

            {/* Content */}
            <div className="space-y-0.5">
                <p
                    className="text-xs font-medium"
                    style={{ color: '#727785' }}
                >
                    {label}
                </p>
                <p
                    className="text-2xl font-bold"
                    style={{ color: '#151c27' }}
                >
                    {value}
                </p>

            </div>
        </div>
    )
}
