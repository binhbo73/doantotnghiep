'use client'

import React from 'react'

export interface NavItem {
    id: string
    label: string
    icon: string
    href: string
    badge?: number
    roles?: string[]
}

export const dashboardNavigation: NavItem[] = [
    {
        id: 'dashboard',
        label: 'Bảng điều khiển',
        icon: '📊',
        href: '/dashboard',
    },
    {
        id: 'my-documents',
        label: 'Tài liệu của tôi',
        icon: '👤',
        href: '/dashboard/my-documents',
        roles: ['MANAGER', 'TRUONG_PHONG', 'USER', 'NHAN_VIEN', 'EMPLOYEE'],
    },
    {
        id: 'documents',
        label: 'Kho tài liệu',
        icon: '📁',
        href: '/dashboard/documents',
    },
    {
        id: 'chat',
        label: 'Chat',
        icon: '💬',
        href: '/dashboard/chat',
    },
    {
        id: 'users',
        label: 'Quản lý người',
        icon: '👥',
        href: '/dashboard/users',
        roles: ['ADMIN'],
    },
    {
        id: 'departments',
        label: 'Phòng ban',
        icon: '🏢',
        href: '/dashboard/departments',
        roles: ['ADMIN', 'MANAGER', 'TRUONG_PHONG', 'USER', 'NHAN_VIEN', 'EMPLOYEE'],
    },
    {
        id: 'roles',
        label: 'Vai trò & Quyền hạn',
        icon: '🔐',
        href: '/dashboard/roles',
        roles: ['ADMIN'],
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
 * ├── /dashboard/chat (Chat)
 * ├── /dashboard/users (Quản lý người)
 * ├── /dashboard/departments (Quản lý Phòng ban)
 * ├── /dashboard/roles (Vai trò & Quyền hạn)
 * ├── /dashboard/projects (Dự án)
 * └── /dashboard/reports (Báo cáo)
 * 
 * All routes are wrapped with DashboardLayout that includes:
 * - Sidebar navigation
 * - Collapsible menu
 * - Bottom action buttons (Upgrade, Help, Logout)
 */
