import React from 'react'
import { useRBAC } from '@/hooks/useRBAC'

interface EffectivePermissionBadgeProps {
    resource?: { my_permission?: any; department_id?: string | null; uploader_id?: string | null; created_by_id?: string | null } | null
    resourceType?: string
}

export function EffectivePermissionBadge({ resource, resourceType }: EffectivePermissionBadgeProps) {
    const { getEffectivePermission } = useRBAC()
    const perm = getEffectivePermission(resource, resourceType)

    const labelMap: Record<string, { text: string; bg: string; color: string }> = {
        admin: { text: 'Quyền quản trị', bg: 'bg-red-50', color: 'text-red-600' },
        write: { text: 'Có thể sửa', bg: 'bg-yellow-50', color: 'text-amber-700' },
        read: { text: 'Chỉ xem', bg: 'bg-slate-50', color: 'text-slate-600' },
        none: { text: 'Không có quyền', bg: 'bg-gray-50', color: 'text-gray-400' },
    }

    const cfg = labelMap[perm] || labelMap.none

    return (
        <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${cfg.bg} ${cfg.color}`}>
            {cfg.text}
        </span>
    )
}

export default EffectivePermissionBadge
