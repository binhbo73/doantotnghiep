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
import { useUsers } from '@/hooks/useUsers'
import { useDocuments } from '@/hooks/useDocuments'
import { useDepartments } from '@/hooks/useDashboardMetrics'
import { useToast } from '@/hooks/useToast'

export default function DashboardPage() {
    const [selectedPeriod, setSelectedPeriod] = useState('7days')
    const [isAddEmployeeDialogOpen, setIsAddEmployeeDialogOpen] = useState(false)
    const [dialogMessage, setDialogMessage] = useState<{ type: 'success' | 'error' | null; text: string }>({
        type: null,
        text: '',
    })
    const { toasts, removeToast, showSuccess, showError } = useToast()

    // Custom hooks - Frontend standard flow
    const { count: userCount, loading: usersLoading, error: usersError, refetch: refetchUsers } = useUsers()
    const { count: documentCount, loading: docsLoading, error: docsError } = useDocuments()
    const { count: departmentCount, loading: deptsLoading, error: deptsError } = useDepartments()

    // Overall loading and error states
    const isLoading = usersLoading || docsLoading || deptsLoading
    const errors = [usersError, docsError, deptsError].filter(Boolean)
    const hasError = errors.length > 0

    // Mock data for stats - will be replaced with real API data
    const stats = [
        {
            id: 'users',
            icon: '👥',
            label: 'SỐ NGƯỜI DÙNG',
            value: isLoading ? '...' : userCount.toLocaleString(),
            trend: 'up' as const,

            iconBgColor: '#f0f3ff',
        },
        {
            id: 'documents',
            icon: '📁',
            label: 'TÀI LIỆU LƯU TRỮ',
            value: isLoading ? '...' : documentCount.toLocaleString(),
            trend: 'up' as const,

            iconBgColor: '#fff4e0',
        },
        {
            id: 'departments',
            icon: '🏢',
            label: 'SỐ PHÒNG BAN',
            value: isLoading ? '...' : departmentCount.toLocaleString(),
            trend: 'neutral' as const,
            iconBgColor: '#e0f2fe',
        },
    ]

    // Quick action buttons
    const quickActions = [
        {
            id: 'add-user',
            label: 'Thêm nhân sự',
            icon: '👤',
            onClick: () => setIsAddEmployeeDialogOpen(true),
        },
        {
            id: 'upload-doc',
            label: 'Tải tài liệu',
            icon: '📤',
            onClick: () => console.log('Upload doc'),
        },
        {
            id: 'view-report',
            label: 'Phản quyền',
            icon: '🔐',
            onClick: () => console.log('View permissions'),
        },
        {
            id: 'settings',
            label: 'Cấu hình AI',
            icon: '⚙️',
            onClick: () => console.log('Settings'),
        },
    ]

    // Recent activities
    const recentActivities = [
        {
            id: 'activity1',
            title: 'Lê Thị Mai đã cập nhật "Tài liệu Marketing Q3"',
            description: 'Được chia sẻ bởi Team Marketing',
            time: 'Hôm nay',
            avatarChar: 'L',
            avatarBgColor: '#0058be',
            category: 'Marketing',
        },
        {
            id: 'activity2',
            title: 'Hệ thống đã phát hiện "12 yêu cầu truy cập mới"',
            description: 'Cần được phê duyệt bởi quản trị viên',
            time: '3 giờ trước',
            avatarChar: 'H',
            avatarBgColor: '#10b981',
            category: 'System',
        },
        {
            id: 'activity3',
            title: 'Trần Anh Quân đã gáp nhật "Dự án: Tối ưu UX/UI"',
            description: 'Được cập nhật bởi Product Team',
            time: '5 giờ trước',
            avatarChar: 'T',
            avatarBgColor: '#924700',
            category: 'Product',
        },
    ]

    const handleExport = () => {
        console.log('Export report')
    }

    const handleViewAllActivities = () => {
        console.log('View all activities')
    }

    const handleAddEmployee = async (formData: any) => {
        try {
            setDialogMessage({ type: null, text: '' })

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

            // Show success toast notification (top-right corner)
            showSuccess(`Tạo tài khoản thành công cho ${result.first_name} ${result.last_name}`)

            // Refetch user count
            await refetchUsers()

            // Close dialog after 1.5 seconds
            setTimeout(() => {
                setIsAddEmployeeDialogOpen(false)
                setDialogMessage({ type: null, text: '' })
            }, 1500)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Có lỗi xảy ra'
            console.error('❌ Error creating employee:', err)
            showError(message)
        }
    }

    return (
        <main
            className="min-h-full"
            style={{
                backgroundColor: '#f9f9ff',
            }}
        >
            {/* Toast Notifications - Top Right */}
            <ToastContainer toasts={toasts} onRemove={removeToast} />

            {/* Add Employee Dialog */}
            <AddEmployeeDialog
                isOpen={isAddEmployeeDialogOpen}
                onClose={() => setIsAddEmployeeDialogOpen(false)}
                onSubmit={handleAddEmployee}
            />

            {/* Dashboard Header - Compact */}
            <div className="px-4 py-3">
                <DashboardHeader
                    userName="Admin"
                    timeOfDay="sáng"
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
                {/* Stats Section - 3 columns grid, compact */}
                <section className="mb-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
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

                {/* Activity Summary Section */}
                <section className="mb-4">
                    <ActivitySummary
                        title="Biểu đồ Hoạt động Tri Thức"
                        subtitle="Lưu ý truy cập & đồng góp kiến thức thực tế các giai đoạn"
                        badges={[
                            {
                                label: 'Tuần này',
                                color: 'success',
                                onClick: () => console.log('This week'),
                            },
                            {
                                label: 'Dùng giấy',
                                color: 'warning',
                                onClick: () => console.log('Draft'),
                            },
                        ]}
                    >
                        {/* Placeholder for chart */}
                        <div
                            className="h-24 rounded-lg flex items-center justify-center text-sm"
                            style={{
                                backgroundColor: '#f0f3ff',
                                color: '#727785',
                            }}
                        >
                            <p>📊 Biểu đồ hoạt động sẽ được hiển thị ở đây</p>
                        </div>
                    </ActivitySummary>
                </section>

                {/* Quick Actions Section */}
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

                {/* Recent Activity Section */}
                <section className="mb-4">
                    <div
                        className="rounded-lg p-4"
                        style={{
                            backgroundColor: '#ffffff',
                            border: '1px solid #dce2f3',
                        }}
                    >
                        <RecentActivityCard
                            activities={recentActivities}
                            onViewAll={handleViewAllActivities}
                        />
                    </div>
                </section>

                {/* Footer */}
                <footer
                    className="text-center text-xs py-4"
                    style={{ color: '#727785' }}
                >
                    <p>© 2024 Enterprise Knowledge OS. Hệ thống quản lý tài liệu tích hợp.</p>
                </footer>
            </div>
        </main>
    )
}
