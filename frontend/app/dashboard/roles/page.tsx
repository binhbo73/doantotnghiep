'use client'

/**
 * Roles & Permissions Page
 * RBAC: Admin-only. Non-admin users see access denied.
 */

import { useRBAC } from '@/hooks/useRBAC'
import { useRouter } from 'next/navigation'
import { RoleManagementPage } from '@/components/features/roles'
import { AccessDeniedPage } from '@/components/common/AccessDeniedPage'

export default function RolesPage() {
    const { isAdmin } = useRBAC()
    const router = useRouter()

    if (!isAdmin()) {
        return (
            <AccessDeniedPage
                title="Truy cập bị hạn chế"
                message="Bạn cần quyền Quản trị viên (Admin) để truy cập trang Vai trò & Quyền hạn. Vui lòng liên hệ quản trị viên hệ thống nếu bạn cần được cấp quyền."
                icon="🔐"
                showBackButton={true}
                onGoBack={() => router.push('/dashboard')}
            />
        )
    }

    return <RoleManagementPage />
}
