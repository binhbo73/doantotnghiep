/**
 * Sub-Departments Section
 * Shows grid of sub-department cards
 */

'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { DepartmentNode } from '@/types/departments';

interface SubDepartmentsSectionProps {
    subDepartments: DepartmentNode[];
}

export default function SubDepartmentsSection({
    subDepartments,
}: SubDepartmentsSectionProps) {
    const router = useRouter();

    const handleNavigate = (deptId: string) => {
        router.push(`/dashboard/departments/${deptId}`);
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#9d4300] text-lg">schema</span>
                <h2 className="text-base font-black text-[#0d1c2e] tracking-tight">
                    Phòng ban con
                </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {subDepartments.map((dept) => (
                    <div
                        key={dept.id}
                        onClick={() => handleNavigate(dept.id)}
                        className="p-3 bg-white rounded-xl border border-[#e0c0b1]/30 hover:border-[#9d4300] hover:shadow-sm transition-all cursor-pointer group relative overflow-hidden"
                    >
                        <div className="relative z-10">
                            <h4 className="text-sm font-bold text-[#0d1c2e] group-hover:text-[#9d4300] transition-colors mb-0.5 truncate pr-6">
                                {dept.name}
                            </h4>
                            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-3">
                                {dept.member_count} nhân sự
                            </p>

                            {/* Avatar Stack - Compact */}
                            <div className="flex -space-x-2 items-center">
                                {[1, 2, 3].map((i) => (
                                    <div key={i} className="w-6 h-6 rounded-full border border-white bg-slate-100 flex items-center justify-center text-[8px] font-bold text-slate-400 overflow-hidden">
                                        <img 
                                            src={`https://i.pravatar.cc/100?img=${(dept.id.charCodeAt(0) + i) % 50}`} 
                                            alt="M"
                                            className="w-full h-full object-cover"
                                        />
                                    </div>
                                ))}
                                {dept.member_count > 3 && (
                                    <div className="w-6 h-6 rounded-full border border-white bg-[#eff4ff] flex items-center justify-center text-[7px] font-bold text-blue-600">
                                        +{dept.member_count - 3}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Background Decoration - Smaller */}
                        <div className="absolute top-1/2 right-2 -translate-y-1/2 opacity-[0.03] scale-110 group-hover:opacity-[0.06] transition-opacity">
                            <span className="material-symbols-outlined text-4xl text-[#9d4300]">hub</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
