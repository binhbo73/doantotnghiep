'use client'

import React from 'react'

export interface NavItem {
    id: string
    label: string
    icon: string
    href: string
    badge?: number
}

export const dashboardNavigation: NavItem[] = [
    {
        id: 'dashboard',
        label: 'Bảng điều khiển',
        icon: '📊',
        href: '/dashboard',
    },
    {
        id: 'documents',
        label: 'Kho tài liệu',
        icon: '📁',
        href: '/dashboard/documents',
    },
    {
        id: 'users',
        label: 'Quản lý người',
        icon: '👥',
        href: '/dashboard/users',
    },
    {
        id: 'projects',
        label: 'Dự án',
        icon: '📋',
        href: '/dashboard/projects',
    },
    {
        id: 'reports',
        label: 'Báo cáo',
        icon: '📈',
        href: '/dashboard/reports',
    },
]

/**
 * Navigation Routes Structure
 * 
 * /dashboard (Main Dashboard - Bảng điều khiển)
 * ├── /dashboard/documents (Kho tài liệu)
 * ├── /dashboard/users (Quản lý người)
 * ├── /dashboard/projects (Dự án)
 * └── /dashboard/reports (Báo cáo)
 * 
 * All routes are wrapped with DashboardLayout that includes:
 * - Sidebar navigation
 * - Collapsible menu
 * - Bottom action buttons (Upgrade, Help, Logout)
 */
