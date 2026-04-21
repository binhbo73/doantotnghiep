/**
 * Staff Table Section with Tab Navigation
 * Shows Users, Folders, or Documents based on active tab
 */

import React from 'react';
import StaffUsersTab from '@/components/departments/tabs/StaffUsersTab';
import StaffFoldersTab from '@/components/departments/tabs/StaffFoldersTab';
import StaffDocumentsTab from '@/components/departments/tabs/StaffDocumentsTab';
import { DepartmentDetail } from '@/types/departments';

type TabType = 'users' | 'folders' | 'documents';

interface StaffTableSectionProps {
    deptId: string;
    activeTab: TabType;
    onTabChange: (tab: TabType) => void;
    departmentDetail: DepartmentDetail;
}

export default function StaffTableSection({
    deptId,
    activeTab,
    onTabChange,
    departmentDetail,
}: StaffTableSectionProps) {
    const tabs: Array<{ id: TabType; label: string; count: number }> = [
        { id: 'users', label: 'Nhân sự', count: departmentDetail.member_count },
        { id: 'folders', label: 'Thư mục', count: departmentDetail.folder_count },
        { id: 'documents', label: 'Tài liệu', count: departmentDetail.document_count },
    ];

    return (
        <div className="space-y-4">
            {/* Header with Stats & Actions - Compact */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2">
                <div className="flex items-baseline gap-2">
                    <h2 className="text-xl font-black text-[#0d1c2e] tracking-tight">
                        Danh sách {activeTab === 'users' ? 'Nhân sự' : activeTab === 'folders' ? 'Thư mục' : 'Tài liệu'}
                    </h2>
                    <span className="text-lg font-bold text-slate-400">
                        ({tabs.find(t => t.id === activeTab)?.count || 0})
                    </span>
                </div>

                <div className="flex items-center gap-1.5">
                    <button className="w-8 h-8 flex items-center justify-center rounded-lg bg-white border border-[#e0c0b1]/30 text-slate-400 text-sm">
                        <span className="material-symbols-outlined text-xl">filter_list</span>
                    </button>
                    <button className="w-8 h-8 flex items-center justify-center rounded-lg bg-white border border-[#e0c0b1]/30 text-slate-400">
                        <span className="material-symbols-outlined text-xl">download</span>
                    </button>
                    <button className="w-8 h-8 flex items-center justify-center rounded-lg bg-[#9d4300] text-white shadow-md ml-1">
                        <span className="material-symbols-outlined text-xl">person_add</span>
                    </button>
                </div>
            </div>

            {/* Tab Navigation - Compact */}
            <div className="flex gap-1 p-1 bg-[#f8f9ff] rounded-xl w-fit">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => onTabChange(tab.id)}
                        className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${activeTab === tab.id
                            ? 'bg-white text-[#9d4300] shadow-sm ring-1 ring-[#e0c0b1]/10'
                            : 'text-slate-400 hover:text-slate-600'
                            }`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Tab Content - Compact */}
            <div className="bg-white rounded-2xl p-4 shadow-sm border border-[#e0c0b1]/20">
                {activeTab === 'users' && (
                    <StaffUsersTab
                        deptId={deptId}
                        initialData={departmentDetail.users}
                    />
                )}
                {activeTab === 'folders' && (
                    <StaffFoldersTab
                        deptId={deptId}
                        initialData={departmentDetail.folders}
                    />
                )}
                {activeTab === 'documents' && (
                    <StaffDocumentsTab
                        deptId={deptId}
                        initialData={departmentDetail.documents}
                    />
                )}
            </div>
        </div>
    );
}
