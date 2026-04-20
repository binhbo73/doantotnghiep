'use client'

interface PerformanceScoreCardProps {
    score: number
    maxScore?: number
    label?: string
}

export function PerformanceScoreCard({
    score,
    maxScore = 100,
    label = 'HIỆU SUẤT THI THỰC',
}: PerformanceScoreCardProps) {
    const percentage = (score / maxScore) * 100

    return (
        <div
            className="rounded-lg p-3 text-white flex flex-col items-center justify-center min-h-[180px]"
            style={{
                backgroundColor: '#b75b00',
                background: 'linear-gradient(135deg, #b75b00 0%, #924700 100%)',
            }}
        >
            {/* Label */}
            <p
                className="text-xs font-medium mb-2 text-center opacity-90"
                style={{ letterSpacing: '0.05em' }}
            >
                {label}
            </p>

            {/* Score Circle */}
            <div className="relative w-24 h-24 mb-2">
                <svg
                    className="w-full h-full transform -rotate-90"
                    viewBox="0 0 120 120"
                >
                    {/* Background circle */}
                    <circle
                        cx="60"
                        cy="60"
                        r="50"
                        fill="none"
                        stroke="rgba(255,255,255,0.2)"
                        strokeWidth="6"
                    />
                    {/* Progress circle */}
                    <circle
                        cx="60"
                        cy="60"
                        r="50"
                        fill="none"
                        stroke="rgba(255,255,255,0.9)"
                        strokeWidth="6"
                        strokeDasharray={`${(percentage / 100) * 2 * Math.PI * 50} ${2 * Math.PI * 50}`}
                        strokeLinecap="round"
                        style={{ transition: 'stroke-dasharray 0.3s ease' }}
                    />
                </svg>
                {/* Score Text */}
                <div
                    className="absolute inset-0 flex items-center justify-center text-white"
                >
                    <span className="text-2xl font-bold">{score}</span>
                    <span className="text-xs ml-0.5 opacity-80">/{maxScore}</span>
                </div>
            </div>

            {/* Description */}
            <p className="text-xs text-center opacity-85">
                Tính từ những dự liệu doanh nghiệp
            </p>
        </div>
    )
}
