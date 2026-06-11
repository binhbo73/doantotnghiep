import React from 'react'
import { useRBAC } from '@/hooks/useRBAC'

interface EffectivePermissionBadgeProps {
    resource?: {
        my_permission?: 'delete' | 'write' | 'read' | 'none' | null
        department_id?: string | null
        uploader_id?: string | null
        created_by_id?: string | null
    } | null
    resourceType?: string
}

export function EffectivePermissionBadge({ resource, resourceType }: EffectivePermissionBadgeProps) {
    const { getEffectivePermission } = useRBAC()
    const permission = resource?.my_permission ?? getEffectivePermission(resource, resourceType)

    const labels = {
        delete: { text: 'Toàn quyền', className: 'bg-red-50 text-red-600' },
        write: { text: 'Có thể cập nhật', className: 'bg-yellow-50 text-amber-700' },
        read: { text: 'Chỉ xem', className: 'bg-slate-50 text-slate-600' },
        none: { text: 'Không có quyền', className: 'bg-gray-50 text-gray-400' },
    }
    const config = labels[permission]

    return (
        <span className={`inline-block rounded px-2 py-0.5 text-[11px] font-semibold ${config.className}`}>
            {config.text}
        </span>
    )
}

export default EffectivePermissionBadge
