'use client'

export interface NavItem {
    id: string
    label: string
    icon: string
    iconName?: string
    href: string
    badge?: number
    permissions?: string[]
    requireAllPermissions?: boolean
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
        iconName: 'description',
        href: '/dashboard/my-documents',
        permissions: ['document_read', 'folder_read'],
        requireAllPermissions: true,
    },
    {
        id: 'documents',
        label: 'Kho tài liệu',
        icon: '📁',
        href: '/dashboard/documents',
        permissions: ['document_read', 'folder_read'],
    },
    {
        id: 'chat',
        label: 'Chat',
        icon: '💬',
        href: '/dashboard/chat',
        permissions: ['chat_read', 'chat_send', 'chat_create'],
    },
    {
        id: 'users',
        label: 'Quản lý người',
        icon: '👥',
        href: '/dashboard/users',
        permissions: ['user_read'],
    },
    {
        id: 'departments',
        label: 'Phòng ban',
        icon: '🏢',
        href: '/dashboard/departments',
        permissions: ['department_read'],
    },
    {
        id: 'roles',
        label: 'Vai trò & Quyền hạn',
        icon: '🔐',
        href: '/dashboard/roles',
        permissions: ['role_manage', 'permission_manage'],
    },
    {
        id: 'deleted',
        label: 'Kh\u00f4i ph\u1ee5c d\u1eef li\u1ec7u',
        icon: 'restore',
        iconName: 'restore',
        href: '/dashboard/deleted',
        permissions: [
            'system_admin',
            'user_delete',
            'department_manage',
            'folder_delete',
            'document_delete',
            'role_manage',
            'permission_manage',
            'audit_log_view',
        ],
    },
    // {
    //     id: 'projects',
    //     label: 'Dự án',
    //     icon: '📋',
    //     href: '/dashboard/projects',
    // },
    // {
    //     id: 'reports',
    //     label: 'Báo cáo',
    //     icon: '📈',
    //     href: '/dashboard/reports',
    // },
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
