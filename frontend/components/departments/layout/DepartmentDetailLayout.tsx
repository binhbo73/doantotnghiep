/**
 * Department Detail Layout
 * Main layout wrapper for department detail page with premium header
 */

'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';

interface DepartmentDetailLayoutProps {
    children: React.ReactNode;
    deptId: string;
}

export default function DepartmentDetailLayout({
    children,
    deptId,
}: DepartmentDetailLayoutProps) {
    const pathname = usePathname();
    const router = useRouter();
    const isStorageTabActive = pathname.endsWith('/storage');

    const handleBack = () => {
        if (window.history.length > 1) {
            router.back();
            return;
        }

        router.push('/dashboard/departments');
    };

    return (
        <div className="min-h-screen bg-[#f8f9ff]">
            {/* Premium Top Bar - Compact */}
            <div className="sticky top-0 z-30 bg-[#f8f9ff]/80 backdrop-blur-xl border-b border-[#e0c0b1]/10 px-6 py-2">
                <div className="max-w-[1600px] mx-auto flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <button
                            type="button"
                            onClick={handleBack}
                            className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[#e0c0b1]/30 bg-white/80 text-[#584237] shadow-sm transition-all hover:-translate-x-0.5 hover:bg-white hover:shadow-md"
                            aria-label="Quay lại danh sách phòng ban"
                        >
                            <span className="material-symbols-outlined text-[22px]">arrow_back</span>
                        </button>

                        {/* Secondary Tabs */}
                        <div className="flex items-center gap-6">
                            <Link
                                href={`/dashboard/departments/${deptId}`}
                                className="relative py-2 text-xs font-black transition-colors"
                                style={{ color: isStorageTabActive ? '#8b9ab6' : '#b45309' }}
                            >
                                Phòng ban
                                {!isStorageTabActive && (
                                    <div className="absolute -bottom-2 left-0 right-0 h-0.5 bg-[#f59e0b] rounded-full" />
                                )}
                            </Link>
                            <Link
                                href={`/dashboard/departments/${deptId}/storage`}
                                className="relative py-2 text-xs font-black transition-colors"
                                style={{ color: isStorageTabActive ? '#b45309' : '#94a3b8' }}
                            >
                                Kho lưu trữ
                                {isStorageTabActive && (
                                    <div className="absolute -bottom-2 left-0 right-0 h-0.5 bg-[#f59e0b] rounded-full" />
                                )}
                            </Link>
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


        </div>
    );
}
