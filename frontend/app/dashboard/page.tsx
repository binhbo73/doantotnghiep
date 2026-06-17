'use client'

import React, { useState } from 'react'
import {
    DashboardHeader,
    StatCard,
    ActivitySummary,
    QuickActionButtons,
    RecentActivityCard,
} from '@/components/features/dashboard'
import AddEmployeeDialog from '@/components/features/dashboard/AddEmployeeDialog'
import { ToastContainer } from '@/components/common/Toast'
import { createEmployee } from '@/services/employee'
import { useDocuments } from '@/hooks/useDocuments'
import { useToast } from '@/hooks/useToast'
import { useRBAC } from '@/hooks/useRBAC'
import { useAuthContext } from '@/context'
import { useRouter } from 'next/navigation'

/**
 * Dashboard Page - permission-aware
 * 
 * Visible stats and quick actions are derived from backend permission codes,
 * so newly created roles work without frontend role-name changes.
 */
export default function DashboardPage() {
    const router = useRouter()
    const [isAddEmployeeDialogOpen, setIsAddEmployeeDialogOpen] = useState(false)
    const { toasts, removeToast, showSuccess, showError } = useToast()
    const { user } = useAuthContext()
    const { hasPermission, hasAnyPermission } = useRBAC()
    const canReadUsers = hasPermission('user_read')
    const canCreateUser = hasPermission('user_create')
    const canReadDepartments = hasPermission('department_read')
    const canReadDocuments = hasPermission('document_read')
    const canUploadDocument = hasPermission('document_create')
    const canManageIam = hasAnyPermission(['role_manage', 'permission_manage'])
    const canViewAudit = hasPermission('audit_log_view')

    // --- RBAC-aware API calls ---
    // Documents API is loaded only when backend permissions allow access.
    const { count: documentCount, loading: docsLoading, error: docsError } = useDocuments(canReadDocuments)

    // Users & Departments API calls are gated by permission codes.
    const [adminStats, setAdminStats] = useState<{ userCount: number; deptCount: number } | null>(null)
    const [adminStatsLoading, setAdminStatsLoading] = useState(false)

    React.useEffect(() => {
        if (!canReadUsers && !canReadDepartments) return

        const fetchAdminStats = async () => {
            setAdminStatsLoading(true)
            try {
                const { api } = await import('@/services/api')
                const [usersRes, deptsRes] = await Promise.allSettled([
                    canReadUsers ? api.get<any>('/users/?page=1&page_size=1') : Promise.resolve(null),
                    canReadDepartments ? api.get<any>('/departments/?page=1&page_size=1') : Promise.resolve(null),
                ])

                const userCount = usersRes.status === 'fulfilled'
                    ? (usersRes.value?.data?.pagination?.total_items || usersRes.value?.pagination?.total_items || 0)
                    : 0
                const deptCount = deptsRes.status === 'fulfilled'
                    ? (deptsRes.value?.data?.pagination?.total_items || deptsRes.value?.pagination?.total_items || 0)
                    : 0

                setAdminStats({ userCount, deptCount })
            } catch (err) {
                console.error('Failed to fetch admin stats:', err)
            } finally {
                setAdminStatsLoading(false)
            }
        }
        fetchAdminStats()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [canReadUsers, canReadDepartments])

    // --- Loading & Error ---
    const isLoading = docsLoading || adminStatsLoading
    const errors = [docsError].filter(Boolean)
    const hasError = errors.length > 0

    // --- Build stats cards based on permission codes ---
    const stats = [
        // user_read: user count
        canReadUsers && {
            id: 'users',
            icon: '👥',
            label: 'SỐ NGƯỜI DÙNG',
            value: isLoading ? '...' : (adminStats?.userCount ?? 0).toLocaleString(),
            trend: 'up' as const,
            iconBgColor: '#f0f3ff',
        },
        // document_read: document count
        canReadDocuments && {
            id: 'documents',
            icon: '📁',
            label: 'TÀI LIỆU LƯU TRỮ',
            value: isLoading ? '...' : documentCount.toLocaleString(),
            trend: 'up' as const,
            iconBgColor: '#fff4e0',
        },
        // department read/update/manage: department count
        canReadDepartments && {
            id: 'departments',
            icon: '🏢',
            label: 'SỐ PHÒNG BAN',
            value: isLoading ? '...' : (adminStats?.deptCount ?? 0).toLocaleString(),
            trend: 'neutral' as const,
            iconBgColor: '#e0f2fe',
        },
    ].filter(Boolean) as any[]

    // --- Quick action buttons based on permission codes ---
    const quickActions = [
        // Add employee/account when user_create is granted.
        canCreateUser && {
            id: 'add-user',
            label: 'Thêm nhân sự',
            icon: '👤',
            onClick: () => setIsAddEmployeeDialogOpen(true),
        },
        // document_create: upload document
        canUploadDocument && {
            id: 'upload-doc',
            label: 'Tải tài liệu',
            icon: '📤',
            onClick: () => router.push('/dashboard/documents'),
        },
        // role_manage/permission_manage: permission management
        canManageIam && {
            id: 'view-report',
            label: 'Phân quyền',
            icon: '🔐',
            onClick: () => router.push('/dashboard/roles'),
        },
        // department read/update/manage: department management
        canReadDepartments && {
            id: 'departments',
            label: 'Phòng ban',
            icon: '🏢',
            onClick: () => router.push('/dashboard/departments'),
        },
    ].filter(Boolean) as any[]

    const handleExport = () => {
        console.log('Export report')
    }

    const handleViewAllActivities = () => {
        console.log('View all activities')
    }

    const handleAddEmployee = async (formData: any) => {
        try {
            // Call API to create employee
            const result = await createEmployee({
                username: formData.username,
                email: formData.email,
                first_name: formData.firstName,
                last_name: formData.lastName,
                department_id: formData.department,
                role_id: formData.role,
            })

            console.log('✅ Employee created:', result)
            showSuccess(`Tạo tài khoản thành công cho ${result.first_name} ${result.last_name}`)

            // Close dialog after 1.5 seconds
            setTimeout(() => {
                setIsAddEmployeeDialogOpen(false)
            }, 1500)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Có lỗi xảy ra'
            console.error('❌ Error creating employee:', err)
            showError(message)
        }
    }

    // --- Determine greeting time ---
    const hour = new Date().getHours()
    const timeOfDay = hour < 12 ? 'sáng' : hour < 18 ? 'chiều' : 'tối'

    return (
        <main
            className="min-h-full"
            style={{
                backgroundColor: '#f9f9ff',
            }}
        >
            {/* Toast Notifications - Top Right */}
            <ToastContainer toasts={toasts} onRemove={removeToast} />

            {/* Add account dialog, shown only when user_create is granted. */}
            {canCreateUser && (
                <AddEmployeeDialog
                    isOpen={isAddEmployeeDialogOpen}
                    onClose={() => setIsAddEmployeeDialogOpen(false)}
                    onSubmit={handleAddEmployee}
                />
            )}

            {/* Dashboard Header - Compact */}
            <div className="px-4 py-3">
                <DashboardHeader
                    userName={user?.name || user?.username || 'Bạn'}
                    timeOfDay={timeOfDay}
                    daysLabel="7 ngày qua"
                    onExport={handleExport}
                />
            </div>

            {/* Error Alert */}
            {hasError && (
                <div className="px-4 py-2 mb-2">
                    <div
                        className="rounded-lg p-3 text-sm"
                        style={{
                            backgroundColor: '#ffe0e0',
                            color: '#d32f2f',
                            border: '1px solid #ffcdd2',
                        }}
                    >
                        ⚠️ {errors[0]}
                    </div>
                </div>
            )}

            {/* Main Content */}
            <div className="px-4 pb-6">
                {/* Stats Section */}
                <section className="mb-4">
                    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-${stats.length > 2 ? '3' : stats.length} gap-3`}>
                        {stats.map((stat) => (
                            <StatCard
                                key={stat.id}
                                icon={stat.icon}
                                label={stat.label}
                                value={stat.value}
                                trend={stat.trend}
                                iconBgColor={stat.iconBgColor}
                            />
                        ))}
                    </div>
                </section>



                {/* Quick actions are filtered by permission codes. */}
                {quickActions.length > 0 && (
                    <section className="mb-4">
                        <div
                            className="rounded-lg p-4"
                            style={{
                                backgroundColor: '#ffffff',
                                border: '1px solid #dce2f3',
                            }}
                        >
                            <h2
                                className="text-sm font-bold mb-3"
                                style={{ color: '#151c27' }}
                            >
                                ⚡ LỐI TẮT QUẢN TRỊ
                            </h2>
                            <QuickActionButtons actions={quickActions} />
                        </div>
                    </section>
                )}

                {/* Recent Activity Section */}
                {canViewAudit && <section className="mb-4">
                    <div
                        className="rounded-lg p-4"
                        style={{
                            backgroundColor: '#ffffff',
                            border: '1px solid #dce2f3',
                        }}
                    >
                        <RecentActivityCard onViewAll={handleViewAllActivities} />
                    </div>
                </section>}

                {/* Footer */}
                <footer
                    className="text-center text-xs py-4"
                    style={{ color: '#727785' }}
                >
                    <p>© 2026 Enterprise Knowledge OS. Hệ thống quản lý tài liệu tích hợp.</p>
                </footer>
            </div>
        </main>
    )
}
