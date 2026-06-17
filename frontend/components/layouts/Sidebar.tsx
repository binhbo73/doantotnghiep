'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { dashboardNavigation } from '@/constants/navigation'
import { useRBAC } from '@/hooks/useRBAC'
import { AppIcon } from '@/components/ui/AppIcon'

interface SidebarProps {
    onLogout?: () => void
    onUpgrade?: () => void
}

export function Sidebar({
    onLogout,
}: SidebarProps) {
    const pathname = usePathname()
    const [isCollapsed, setIsCollapsed] = useState(false)

    const isActive = (href: string) => {
        if (href === '/dashboard') {
            return pathname === '/dashboard' || pathname === '/dashboard/'
        }
        return pathname.startsWith(href)
    }

    const { hasAnyPermission, hasAllPermissions, isAdmin } = useRBAC()

    // Filter navigation based on permissions
    const filteredNavigation = dashboardNavigation.filter(item => {
        if (!item.permissions || item.permissions.length === 0) return true
        if (isAdmin()) return true

        if (item.requireAllPermissions) {
            return hasAllPermissions(item.permissions)
        }
        return hasAnyPermission(item.permissions)
    })

    return (
        <aside
            className="flex flex-col h-screen max-h-screen overflow-hidden transition-all duration-300 relative z-50"
            style={{
                width: isCollapsed ? '80px' : '240px',
                backgroundColor: '#ffffff',
                borderRight: '1px solid #dce2f3',
                boxShadow: '0 0 1px rgba(0, 0, 0, 0.05)',
            }}
        >
            {/* Logo Section */}
            <div
                className="flex items-center justify-between px-2 py-4 border-b flex-shrink-0"
                style={{ borderColor: '#dce2f3' }}
            >
                <Link
                    href="/dashboard/profile"
                    className="flex items-center gap-2 transition-all flex-1 overflow-hidden hover:opacity-80"
                    style={{
                        opacity: isCollapsed ? 0 : 1,
                        maxWidth: isCollapsed ? '0px' : '100%',
                        width: isCollapsed ? '0px' : 'auto',
                    }}
                    title="Hồ sơ cá nhân"
                >
                    <div
                        className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-white text-sm flex-shrink-0"
                        style={{ backgroundColor: '#b75b00' }}
                    >
                        K
                    </div>
                    <span
                        className="font-bold text-sm whitespace-nowrap"
                        style={{ color: '#151c27' }}
                    >
                        Knowledge OS
                    </span>
                </Link>

                {/* Toggle Button - Always Visible */}
                <button
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    className="p-2 rounded-md transition-all hover:bg-gray-200 flex-shrink-0 flex items-center justify-center"
                    style={{
                        backgroundColor: '#fff7ed',
                        minWidth: '36px',
                        minHeight: '36px',
                    }}
                    title={isCollapsed ? 'Mở rộng' : 'Thu vào'}
                >
                    <span className="text-lg">
                        {isCollapsed ? '→' : '←'}
                    </span>
                </button>
            </div>

            {/* Navigation Items */}
            <nav className="flex-1 min-h-0 overflow-y-auto px-3 py-4">
                <div className="space-y-1">
                    {filteredNavigation.map((item) => {
                        const active = isActive(item.href)
                        return (
                            <Link
                                key={item.id}
                                href={item.href}
                                className="flex items-center gap-3 px-3 py-3 rounded-lg transition-all relative group"
                                style={{
                                    backgroundColor: active
                                        ? '#fff7ed'
                                        : 'transparent',
                                    color: active ? '#b75b00' : '#424754',
                                }}
                                title={item.label}
                            >
                                {/* Icon */}
                                <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center">
                                    {item.iconName ? (
                                        <AppIcon
                                            name={item.iconName}
                                            className="h-[22px] w-[22px]"
                                            strokeWidth={2}
                                        />
                                    ) : (
                                        <span className="text-lg leading-none">{item.icon}</span>
                                    )}
                                </span>

                                {/* Label */}
                                <span
                                    className="text-sm font-medium transition-opacity whitespace-nowrap overflow-hidden"
                                    style={{
                                        opacity: isCollapsed ? 0 : 1,
                                        maxWidth: isCollapsed ? '0' : '100%',
                                    }}
                                >
                                    {item.label}
                                </span>

                                {/* Active Indicator */}
                                {active && (
                                    <div
                                        className="absolute left-0 top-1/2 w-1 h-6 rounded-r-lg -translate-y-1/2"
                                        style={{
                                            backgroundColor:
                                                '#b75b00',
                                        }}
                                    />
                                )}
                            </Link>
                        )
                    })}
                </div>
            </nav>

            {/* Bottom Actions */}
            <div
                className="px-3 py-4 border-t space-y-2 flex-shrink-0"
                style={{ borderColor: '#dce2f3' }}
            >
                {/* Logout */}
                <button
                    onClick={onLogout}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${isCollapsed ? 'justify-center' : 'justify-start'}`}
                    style={{
                        backgroundColor: '#f9f9ff',
                        color: '#727785',
                        border: '1px solid #dce2f3',
                    }}
                    title="Logout"
                >
                    <span className="flex-shrink-0">🚪</span>
                    <span
                        className="transition-all whitespace-nowrap overflow-hidden"
                        style={{
                            opacity: isCollapsed ? 0 : 1,
                            maxWidth: isCollapsed ? '0px' : '100%',
                            width: isCollapsed ? '0px' : 'auto',
                        }}
                    >
                        Đăng xuất
                    </span>
                </button>
            </div>
        </aside>
    )
}
