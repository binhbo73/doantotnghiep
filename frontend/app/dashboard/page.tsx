'use client'

import React, { useState } from 'react'
import {
    DashboardHeader,
    StatCard,
    ActivitySummary,
    QuickActionButtons,
    RecentActivityCard,
} from '@/components/features/dashboard'
import { useUsers } from '@/hooks/useUsers'
import { useDocuments } from '@/hooks/useDocuments'
import { useDepartments } from '@/hooks/useDashboardMetrics'

export default function DashboardPage() {
    const [selectedPeriod, setSelectedPeriod] = useState('7days')

    // Custom hooks - Frontend standard flow
    const { count: userCount, loading: usersLoading, error: usersError } = useUsers()
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
            onClick: () => console.log('Add user'),
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

    return (
        <main
            className="min-h-full"
            style={{
                backgroundColor: '#f9f9ff',
            }}
        >
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
                        title="Biểu đồ Hoạt động Trị Thức"
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
                            ⚡ LỐI TẠT QUẢN TRỊ
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
