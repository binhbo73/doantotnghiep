/**
 * Info Cards Section
 * Shows action cards: Onboarding, Meeting Schedule, KPI & Metrics
 */

import React from 'react';
import Link from 'next/link';

interface InfoCardsSectionProps {
    deptId: string;
    departmentName: string;
}
export default function InfoCardsSection({
    deptId,
    departmentName,
}: InfoCardsSectionProps) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Card 1: Onboarding - Compact */}
            <div className="p-5 bg-white border border-[#9d4300]/20 rounded-2xl shadow-sm hover:shadow-md transition-all group overflow-hidden relative">
                <div className="relative z-10 space-y-3">
                    <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-[#9d4300] bg-[#fff6f1] p-1.5 rounded-lg text-lg">description</span>
                        <h3 className="text-base font-black text-[#0d1c2e]">
                            Tài liệu Onboarding
                        </h3>
                    </div>
                    <p className="text-xs font-medium text-slate-500 leading-snug">
                        Quy trình gia nhập cho nhân sự mới của {departmentName}.
                    </p>
                    <Link
                        href={`/dashboard/departments/${deptId}/onboarding`}
                        className="inline-flex items-center gap-1.5 text-xs font-black text-[#9d4300] group-hover:gap-3 transition-all"
                    >
                        Truy cập
                        <span className="material-symbols-outlined text-base">arrow_forward</span>
                    </Link>
                </div>
                <span className="absolute -right-2 -bottom-2 text-5xl opacity-[0.03] text-[#9d4300]">article</span>
            </div>

            {/* Card 2: Meeting Schedule - Compact */}
            <div className="p-5 bg-white border border-blue-200 rounded-2xl shadow-sm hover:shadow-md transition-all group overflow-hidden relative">
                <div className="relative z-10 space-y-3">
                    <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-blue-600 bg-blue-50 p-1.5 rounded-lg text-lg">calendar_month</span>
                        <h3 className="text-base font-black text-[#0d1c2e]">
                            Lịch họp định kỳ
                        </h3>
                    </div>
                    <p className="text-xs font-medium text-slate-500 leading-snug">
                        Thứ Hai hàng tuần lúc 09:00 AM tại phòng Apollo.
                    </p>
                    <Link
                        href={`/dashboard/departments/${deptId}/meetings`}
                        className="inline-flex items-center gap-1.5 text-xs font-black text-blue-600 group-hover:gap-3 transition-all"
                    >
                        Xem lịch
                        <span className="material-symbols-outlined text-base">arrow_forward</span>
                    </Link>
                </div>
                <span className="absolute -right-2 -bottom-2 text-5xl opacity-[0.03] text-blue-600">event</span>
            </div>

            {/* Card 3: KPI & Metrics - Compact */}
            <div className="p-5 bg-white border border-rose-200 rounded-2xl shadow-sm hover:shadow-md transition-all group overflow-hidden relative">
                <div className="relative z-10 space-y-3">
                    <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-rose-500 bg-rose-50 p-1.5 rounded-lg text-lg">trending_up</span>
                        <h3 className="text-base font-black text-[#0d1c2e]">
                            KPI & Hiệu suất
                        </h3>
                    </div>
                    <p className="text-xs font-medium text-slate-500 leading-snug">
                        Tiến độ dự án và chỉ số hoàn thành quý III.
                    </p>
                    <Link
                        href={`/dashboard/departments/${deptId}/kpi`}
                        className="inline-flex items-center gap-1.5 text-xs font-black text-rose-500 group-hover:gap-3 transition-all"
                    >
                        Báo cáo
                        <span className="material-symbols-outlined text-base">arrow_forward</span>
                    </Link>
                </div>
                <span className="absolute -right-2 -bottom-2 text-5xl opacity-[0.03] text-rose-500">monitoring</span>
            </div>
        </div>
    );
}
