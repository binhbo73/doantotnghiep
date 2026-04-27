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
                <nav className="hidden lg:flex items-center gap-6">
                    {tabs.map((tab) => (
                        <a
                            key={tab.value}
                            href="#"
                            className={`font-medium text-sm transition-colors duration-200 px-2 py-1 ${tab.active
                                    ? 'text-orange-600 dark:text-orange-500 font-bold border-b-2 border-orange-600 dark:border-orange-500 pb-1'
                                    : 'text-slate-600 dark:text-slate-400 hover:bg-orange-50 dark:hover:bg-orange-900/20'
                                }`}
                        >
                            {tab.label}
                        </a>
                    ))}
                </nav>
            </div>

            <div className="flex items-center gap-4">
                <button className="flex items-center gap-2 p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors">
                    <Bell size={20} />
                </button>
                <button className="flex items-center gap-2 p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors">
                    <Settings size={20} />
                </button>
                <div className="w-8 h-8 rounded-full overflow-hidden border border-slate-200 dark:border-slate-700 bg-gradient-to-br from-orange-300 to-orange-500 flex items-center justify-center text-white text-sm font-bold">
                    A
                </div>
            </div>
        </header>
    )
}
