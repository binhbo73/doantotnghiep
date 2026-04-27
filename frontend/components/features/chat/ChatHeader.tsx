'use client'

import React from 'react'
import { Bell, Settings, LogOut } from 'lucide-react'
import { useRouter } from 'next/navigation'

interface ChatHeaderProps {
    title?: string
    onLogout?: () => void
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
    title = 'Tri thức Doanh nghiệp',
    onLogout,
}) => {
    const router = useRouter()
    const tabs = [
        { label: 'Tổng quan', value: 'overview' },
        { label: 'Tài liệu', value: 'documents', active: true },
        { label: 'Wiki', value: 'wiki' },
        { label: 'Cộng tác', value: 'collaboration' },
    ]

    return (
        <header className="bg-white/80 dark:bg-slate-950/80 backdrop-blur-lg flex justify-between items-center px-8 h-16 sticky top-0 z-50 shadow-sm">
            <div className="flex items-center gap-8 flex-1">
                <span className="text-xl font-black text-orange-600 dark:text-orange-500 tracking-tighter">
                    {title}
                </span>
               
            </div>

           
        </header>
    )
}
