'use client'

interface ErrorAlertCardProps {
    title?: string
    description?: string
    actionLabel?: string
    onViewAll?: () => void
}

export function ErrorAlertCard({
    title = '🚨 LỖI VÀ CẢ NHÂN',
    description = 'Có vụ việc độc lập về kinh doanh hoạt động "Quỹ hoàn hành 2024". Hãy tìm hiểu chi tiết tại đây những điều cần điều chỉnh ngay từ cấp.',
    actionLabel = 'XEM CHI TIẾT HÀNH ĐỘNG',
    onViewAll,
}: ErrorAlertCardProps) {
    return (
        <div
            className="rounded-lg p-3"
            style={{
                backgroundColor: '#ffdcc6',
                border: '1px solid #ffb786',
            }}
        >
            {/* Title */}
            <h3
                className="text-sm font-bold mb-1"
                style={{ color: '#723600' }}
            >
                {title}
            </h3>

            {/* Description */}
            <p
                className="text-xs mb-2 leading-relaxed"
                style={{ color: '#553000' }}
            >
                {description}
            </p>

            {/* Action Link */}
            <button
                onClick={onViewAll}
                className="text-xs font-medium hover:underline transition-all"
                style={{ color: '#b75b00' }}
            >
                {actionLabel}
            </button>
        </div>
    )
}
