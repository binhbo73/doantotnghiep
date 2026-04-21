/**
 * Department Detail Layout
 * Main layout wrapper for department detail page with premium header
 */

'use client';

import React from 'react';
import Link from 'next/link';

interface DepartmentDetailLayoutProps {
    children: React.ReactNode;
    deptId: string;
}

export default function DepartmentDetailLayout({
    children,
    deptId,
}: DepartmentDetailLayoutProps) {
    return (
        <div className="min-h-screen bg-[#f8f9ff]">
            {/* Premium Top Bar - Compact */}
            <div className="sticky top-0 z-30 bg-[#f8f9ff]/80 backdrop-blur-xl border-b border-[#e0c0b1]/10 px-6 py-2">
                <div className="max-w-[1600px] mx-auto flex items-center justify-between">
                    {/* Secondary Tabs */}
                    <div className="flex items-center gap-6">
                        <Link href={`/dashboard/departments/${deptId}`} className="relative py-2 text-xs font-black text-[#9d4300]">
                            Phòng ban
                            <div className="absolute -bottom-2 left-0 right-0 h-0.5 bg-[#9d4300] rounded-full" />
                        </Link>
                        <Link href={`/dashboard/departments/${deptId}/storage`} className="py-2 text-xs font-bold text-slate-400 hover:text-slate-600 transition-colors">
                            Kho lưu trữ
                        </Link>
                    </div>

                    {/* Search & Profile Icons */}
                    <div className="flex items-center gap-4">
                        <div className="relative group">
                            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-lg">search</span>
                            <input 
                                type="text" 
                                placeholder="Tìm kiếm..." 
                                className="pl-10 pr-4 py-2 bg-white border border-[#e0c0b1]/20 rounded-xl text-xs font-medium w-[240px] focus:outline-none focus:ring-2 focus:ring-[#9d4300]/10 transition-all shadow-sm"
                            />
                        </div>

                        <button className="relative w-9 h-9 flex items-center justify-center rounded-xl bg-white border border-[#e0c0b1]/10 text-slate-400">
                            <span className="material-symbols-outlined text-xl">notifications</span>
                            <div className="absolute top-2 right-2 w-1.5 h-1.5 bg-red-500 rounded-full border border-white" />
                        </button>

                        <div className="w-9 h-9 rounded-xl overflow-hidden ring-1 ring-slate-100">
                            <img src="https://i.pravatar.cc/100?u=current-user" alt="User" className="w-full h-full object-cover" />
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content Container - Compact */}
            <div className="max-w-[1600px] mx-auto px-6 py-6 font-sans">
                {/* Content */}
                <div className="space-y-8 text-sm">
                    {children}
                </div>
            </div>

            {/* Footer */}
            <footer className="mt-20 py-12 px-8 border-t border-[#e0c0b1]/10 bg-white/50 backdrop-blur-sm">
                <div className="max-w-[1600px] mx-auto text-center">
                    <p className="text-sm font-bold text-slate-300 uppercase tracking-widest">
                        © 2026 Enterprise Knowledge Operating System • Cognitive Architect
                    </p>
                </div>
            </footer>
        </div>
    );
}
