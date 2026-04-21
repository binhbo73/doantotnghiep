/**
 * Department Detail Header Section
 * Shows department name, description, and action buttons
 */

import React from 'react';
import Link from 'next/link';
import { DepartmentDetail } from '@/types/departments';

interface DepartmentDetailHeaderProps {
    department: DepartmentDetail;
    deptId: string;
}

export default function DepartmentDetailHeader({
    department,
    deptId,
}: DepartmentDetailHeaderProps) {
    return (
        <div className="space-y-4">
            {/* Breadcrumb Navigation - Compact */}
            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[#584237]/60">
                <span className="material-symbols-outlined text-xs">corporate_fare</span>
                <span>KHỐI CÔNG NGHỆ</span>
                <span className="text-slate-300">›</span>
                <span className="text-[#9d4300]">Chi tiết</span>
            </div>

            <div className="flex items-center justify-between">
                {/* Left: Title & Description */}
                <div className="flex-1">
                    <h1 className="text-3xl font-black text-[#0d1c2e] tracking-tight mb-2">
                        {department.name}
                    </h1>
                    {department.description && (
                        <p className="text-sm text-slate-500 max-w-2xl leading-snug">
                            {department.description}
                        </p>
                    )}
                </div>

                {/* Right: Action Buttons - Compact */}
                <div className="flex items-center gap-2">
                    <button className="flex items-center gap-1.5 px-4 py-2.5 bg-[#eff4ff] text-[#0d1c2e] text-xs font-bold rounded-xl hover:bg-[#dce9ff] transition-all border border-blue-100">
                        <span className="material-symbols-outlined text-lg">folder_shared</span>
                        Tài liệu
                    </button>
                    
                    <Link
                        href={`/dashboard/department/${deptId}/edit`}
                        className="flex items-center gap-1.5 px-4 py-2.5 bg-[#9d4300] text-white text-xs font-bold rounded-xl hover:bg-[#853900] transition-all shadow-md active:scale-95"
                    >
                        <span className="material-symbols-outlined text-lg">edit</span>
                        Sửa
                    </Link>
                </div>
            </div>
        </div>
    );
}
