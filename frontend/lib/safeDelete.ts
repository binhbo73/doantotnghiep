import { ApiError } from '@/services/api'

type ErrorEnvelope = {
    data?: {
        blockers?: unknown
    }
    blockers?: unknown
}

export function getSafeDeleteBlockers(error: unknown): Record<string, number> | null {
    if (!(error instanceof ApiError) || error.statusCode !== 409) {
        return null
    }

    const envelope = error.data as ErrorEnvelope | null
    const rawBlockers = envelope?.data?.blockers ?? envelope?.blockers

    if (!rawBlockers || typeof rawBlockers !== 'object') {
        return {}
    }

    return Object.fromEntries(
        Object.entries(rawBlockers)
            .map(([key, value]) => [key, Number(value)] as const)
            .filter(([, value]) => Number.isFinite(value) && value > 0)
    )
}
