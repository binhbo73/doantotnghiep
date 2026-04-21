/**
 * Manager Card Section
 * Shows department manager/head information
 */

import React from 'react';
import Image from 'next/image';
import { UserDetail } from '@/types/departments';

interface ManagerCardProps {
    manager: UserDetail | null | undefined;
    deptId: string;
}

export default function ManagerCard({
    manager,
}: ManagerCardProps) {
    if (!manager) {
        return (
            <div className="p-4 bg-white rounded-2xl border border-[#e0c0b1]/30 flex items-center justify-center min-h-[200px]">
                <div className="text-center space-y-2">
                    <div className="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center mx-auto">
                        <span className="material-symbols-outlined text-slate-300 text-2xl">person_off</span>
                    </div>
                    <p className="text-xs font-medium text-slate-400">Chưa có Trưởng phòng</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-4 bg-white rounded-2xl shadow-sm border border-[#e0c0b1]/30 hover:shadow-md transition-all group">
            <div className="flex justify-between items-start mb-4">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#fff6f1] text-[#9d4300] text-[9px] font-bold uppercase tracking-widest rounded-full">
                    <span className="material-symbols-outlined text-[10px]">verified_user</span>
                    Quản lý
                </span>
                <span className="material-symbols-outlined text-slate-200 text-lg">verified</span>
            </div>

            <div className="flex items-center gap-4 mb-6">
                {/* Avatar - Compact */}
                <div className="relative">
                    <div className="w-16 h-16 rounded-xl overflow-hidden ring-2 ring-slate-50 shadow-inner">
                        {manager.avatar_url ? (
                            <Image
                                src={manager.avatar_url}
                                alt={manager.full_name}
                                width={64}
                                height={64}
                                className="object-cover w-full h-full"
                            />
                        ) : (
                            <div className="w-full h-full bg-gradient-to-br from-[#eff4ff] to-[#dce9ff] flex items-center justify-center">
                                <span className="text-xl font-black text-blue-600">
                                    {manager.full_name?.charAt(0) || '?'}
                                </span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Info - Compact */}
                <div className="min-w-0">
                    <h4 className="text-base font-black text-[#0d1c2e] leading-tight truncate">
                        {manager.full_name}
                    </h4>
                    <p className="text-[9px] font-bold text-slate-400 mt-1 uppercase tracking-wider">
                        ID: #{manager.id.substring(0, 4).toUpperCase()}
                    </p>
                </div>
            </div>

            {/* Contact Info - Compact */}
            <div className="space-y-2 mb-6">
                <div className="flex items-center gap-2 text-slate-600">
                    <span className="material-symbols-outlined text-base text-[#9d4300]/60">mail</span>
                    <span className="text-xs font-medium truncate">{manager.email}</span>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                    <span className="material-symbols-outlined text-base text-[#9d4300]/60">call</span>
                    <span className="text-xs font-medium">+84 902 123 456</span>
                </div>
            </div>

            {/* Action Button - Compact */}
            <button className="w-full py-3 px-4 border border-slate-100 rounded-xl text-slate-900 font-bold text-xs hover:border-[#9d4300] hover:bg-[#fff9f5] transition-all">
                Xem hồ sơ
            </button>
        </div>
    );
}
