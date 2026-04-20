'use client'

import React from 'react'
import { Sidebar } from './Sidebar'
import { useLogout } from '@/hooks/useLogout'

interface DashboardLayoutProps {
    children: React.ReactNode
    onLogout?: () => void
}

export function DashboardLayout({
    children,
    onLogout,
}: DashboardLayoutProps) {
    const { logout } = useLogout()

    const handleLogout = () => {
        logout()
    }

    const handleUpgrade = () => {
        console.log('Upgrade workspace')
    }

    return (
        <div className="flex h-screen overflow-hidden">
            {/* Sidebar */}
            <Sidebar
                onLogout={handleLogout}
                onUpgrade={handleUpgrade}
            />

            {/* Main Content */}
            <main
                className="flex-1 overflow-y-auto overflow-x-hidden"
                style={{
                    backgroundColor: '#f9f9ff',
                }}
            >
                {children}
            </main>
        </div>
    )
}
