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
