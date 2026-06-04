'use client'

/**
 * Roles & Permissions Page
 * RBAC: rendered from role_manage/permission_manage backend permissions.
 */

import { useRBAC } from '@/hooks/useRBAC'
import { useRouter } from 'next/navigation'
import { RoleManagementPage } from '@/components/features/roles'
import { AccessDeniedPage } from '@/components/common/AccessDeniedPage'

export default function RolesPage() {
    const { hasAnyPermission } = useRBAC()
    const router = useRouter()
    const canManageRoles = hasAnyPermission(['role_manage', 'permission_manage'])

    if (!canManageRoles) {
        return (
            <AccessDeniedPage
                title="Truy cập bị hạn chế"
                message="Bạn cần quyền role_manage hoặc permission_manage để truy cập trang Vai trò & Quyền hạn. Vui lòng liên hệ quản trị viên hệ thống nếu bạn cần được cấp quyền."
                icon="🔐"
                showBackButton={true}
                onGoBack={() => router.push('/dashboard')}
            />
        )
    }

    return <RoleManagementPage />
}
