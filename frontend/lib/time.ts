export function formatRelativeTime(input?: string | Date | number) {
    if (!input) return ''

    const date = typeof input === 'string' || typeof input === 'number' ? new Date(input) : input
    if (isNaN(date.getTime())) return ''

    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffSeconds = Math.floor(diffMs / 1000)
    const diffMinutes = Math.floor(diffSeconds / 60)
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)
    const diffMonths = Math.floor(diffDays / 30)
    const diffYears = Math.floor(diffDays / 365)

    const rtf = new Intl.RelativeTimeFormat('vi', { numeric: 'auto' })

    if (diffSeconds < 60) return rtf.format(-diffSeconds, 'second')
    if (diffMinutes < 60) return rtf.format(-diffMinutes, 'minute')
    if (diffHours < 24) return rtf.format(-diffHours, 'hour')
    if (diffDays < 30) return rtf.format(-diffDays, 'day')
    if (diffMonths < 12) return rtf.format(-diffMonths, 'month')
    return rtf.format(-diffYears, 'year')
}

export function formatAbsoluteShort(input?: string | Date | number) {
    if (!input) return ''
    const date = typeof input === 'string' || typeof input === 'number' ? new Date(input) : input
    if (isNaN(date.getTime())) return ''
    return new Intl.DateTimeFormat('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
        day: '2-digit',
        month: '2-digit',
    }).format(date)
}
