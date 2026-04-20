'use client'

interface ActivitySummaryProps {
    title?: string
    subtitle?: string
    badges?: Array<{ label: string; color: 'success' | 'warning'; onClick?: () => void }>
    children?: React.ReactNode
}

export function ActivitySummary({
    title = 'Biểu đồ Hoạt động Trị Thức',
    subtitle = 'Lưu ý truy cập & đồng góp kiến thức thực tế các giai đoạn',
    badges,
    children,
}: ActivitySummaryProps) {
    return (
        <div
            className="rounded-lg p-3"
            style={{
                backgroundColor: '#ffffff',
                border: '1px solid #dce2f3',
            }}
        >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
                <div>
                    <h3
                        className="text-sm font-bold mb-0.5"
                        style={{ color: '#151c27' }}
                    >
                        {title}
                    </h3>
                    <p
                        className="text-xs"
                        style={{ color: '#727785' }}
                    >
                        {subtitle}
                    </p>
                </div>

                {/* Badges */}
                {badges && badges.length > 0 && (
                    <div className="flex gap-1">
                        {badges.map((badge, idx) => (
                            <button
                                key={idx}
                                onClick={badge.onClick}
                                className="px-2 py-0.5 rounded-md text-xs font-medium transition-all"
                                style={{
                                    backgroundColor:
                                        badge.color === 'success'
                                            ? '#d8e2ff'
                                            : '#fff4e0',
                                    color:
                                        badge.color === 'success'
                                            ? '#0058be'
                                            : '#924700',
                                }}
                            >
                                {badge.label}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Content */}
            {children}
        </div>
    )
}
