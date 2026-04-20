'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { dashboardNavigation } from '@/constants/navigation'

interface SidebarProps {
    onLogout?: () => void
    onUpgrade?: () => void
}

export function Sidebar({
    onLogout,
    onUpgrade,
}: SidebarProps) {
    const pathname = usePathname()
    const [isCollapsed, setIsCollapsed] = useState(false)

    const isActive = (href: string) => {
        if (href === '/dashboard') {
            return pathname === '/dashboard' || pathname === '/dashboard/'
        }
        return pathname.startsWith(href)
    }

    return (
        <aside
            className="flex flex-col h-screen transition-all duration-300"
            style={{
                width: isCollapsed ? '80px' : '240px',
                backgroundColor: '#ffffff',
                borderRight: '1px solid #dce2f3',
                boxShadow: '0 0 1px rgba(0, 0, 0, 0.05)',
            }}
        >
            {/* Logo Section */}
            <div
                className="flex items-center justify-between px-2 py-4 border-b"
                style={{ borderColor: '#dce2f3' }}
            >
                <div
                    className="flex items-center gap-2 transition-all flex-1 overflow-hidden"
                    style={{
                        opacity: isCollapsed ? 0 : 1,
                        maxWidth: isCollapsed ? '0px' : '100%',
                        width: isCollapsed ? '0px' : 'auto',
                    }}
                >
                    <div
                        className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-white text-sm flex-shrink-0"
                        style={{ backgroundColor: '#0058be' }}
                    >
                        K
                    </div>
                    <span
                        className="font-bold text-sm whitespace-nowrap"
                        style={{ color: '#151c27' }}
                    >
                        Knowledge OS
                    </span>
                </div>

                {/* Toggle Button - Always Visible */}
                <button
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    className="p-2 rounded-md transition-all hover:bg-gray-200 flex-shrink-0 flex items-center justify-center"
                    style={{
                        backgroundColor: '#f0f3ff',
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
            <nav className="flex-1 px-3 py-4">
                <div className="space-y-1">
                    {dashboardNavigation.map((item) => {
                        const active = isActive(item.href)
                        return (
                            <Link
                                key={item.id}
                                href={item.href}
                                className="flex items-center gap-3 px-3 py-3 rounded-lg transition-all relative group"
                                style={{
                                    backgroundColor: active
                                        ? '#f0f3ff'
                                        : 'transparent',
                                    color: active ? '#0058be' : '#424754',
                                }}
                                title={item.label}
                            >
                                {/* Icon */}
                                <span className="text-lg flex-shrink-0">
                                    {item.icon}
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

                                {/* Badge */}
                                {item.badge && !isCollapsed && (
                                    <span
                                        className="ml-auto px-2 py-1 rounded-full text-xs font-bold"
                                        style={{
                                            backgroundColor:
                                                '#d8e2ff',
                                            color: '#0058be',
                                        }}
                                    >
                                        {item.badge}
                                    </span>
                                )}

                                {/* Active Indicator */}
                                {active && (
                                    <div
                                        className="absolute left-0 top-1/2 w-1 h-6 rounded-r-lg -translate-y-1/2"
                                        style={{
                                            backgroundColor:
                                                '#0058be',
                                        }}
                                    />
                                )}

                                {/* Tooltip */}
                                {isCollapsed && (
                                    <div
                                        className="absolute left-full ml-2 px-2 py-1 rounded-md text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50"
                                        style={{
                                            backgroundColor:
                                                '#151c27',
                                            color: '#ffffff',
                                        }}
                                    >
                                        {item.label}
                                    </div>
                                )}
                            </Link>
                        )
                    })}
                </div>
            </nav>

            {/* Bottom Actions */}
            <div
                className="px-3 py-4 border-t space-y-2"
                style={{ borderColor: '#dce2f3' }}
            >
                {/* Upgrade Button */}
                <button
                    onClick={onUpgrade}
                    className={`w-full flex items-center gap-2 px-3 py-3 rounded-lg font-medium transition-all text-white ${isCollapsed ? 'justify-center' : 'justify-start'}`}
                    style={{
                        backgroundColor: '#b75b00',
                    }}
                    title="Upgrade Workspace"
                >
                    <span className="flex-shrink-0">⭐</span>
                    <span
                        className="transition-all whitespace-nowrap overflow-hidden"
                        style={{
                            opacity: isCollapsed ? 0 : 1,
                            maxWidth: isCollapsed ? '0px' : '100%',
                            width: isCollapsed ? '0px' : 'auto',
                        }}
                    >
                        Nâng cấp
                    </span>
                </button>

                {/* Help Center */}
                <button
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${isCollapsed ? 'justify-center' : 'justify-start'}`}
                    style={{
                        backgroundColor: '#f0f3ff',
                        color: '#0058be',
                    }}
                    title="Help Center"
                >
                    <span className="flex-shrink-0">❓</span>
                    <span
                        className="transition-all whitespace-nowrap overflow-hidden"
                        style={{
                            opacity: isCollapsed ? 0 : 1,
                            maxWidth: isCollapsed ? '0px' : '100%',
                            width: isCollapsed ? '0px' : 'auto',
                        }}
                    >
                        Trợ giúp
                    </span>
                </button>

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
