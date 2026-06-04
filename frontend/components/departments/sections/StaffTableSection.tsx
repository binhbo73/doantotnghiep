/**
 * Staff Table Section with Tab Navigation
 * Shows users, folders, or documents based on available permission codes.
 */

import React, { useEffect, useMemo } from 'react';
import StaffUsersTab from '@/components/departments/tabs/StaffUsersTab';
import StaffFoldersTab from '@/components/departments/tabs/StaffFoldersTab';
import StaffDocumentsTab from '@/components/departments/tabs/StaffDocumentsTab';
import { DepartmentDetail } from '@/types/departments';
import { useRBAC } from '@/hooks/useRBAC';

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
    const { hasPermission } = useRBAC();
    const canViewUsers = hasPermission('user_read');
    const canViewFolders = hasPermission('folder_read') && hasPermission('document_read');
    const canViewDocuments = hasPermission('document_read');

    const tabs = useMemo(() => ([
        canViewUsers && { id: 'users' as const, label: 'Nhân sự', count: departmentDetail.member_count },
        canViewFolders && { id: 'folders' as const, label: 'Thư mục', count: departmentDetail.folder_count },
        canViewDocuments && { id: 'documents' as const, label: 'Tài liệu', count: departmentDetail.document_count },
    ].filter(Boolean) as Array<{ id: TabType; label: string; count: number }>), [
        canViewUsers,
        canViewDocuments,
        canViewFolders,
        departmentDetail.document_count,
        departmentDetail.folder_count,
        departmentDetail.member_count,
    ]);

    useEffect(() => {
        if (!tabs.some((tab) => tab.id === activeTab) && tabs[0]) {
            onTabChange(tabs[0].id);
        }
    }, [activeTab, onTabChange, tabs]);

    const effectiveActiveTab = tabs.some((tab) => tab.id === activeTab)
        ? activeTab
        : tabs[0]?.id;
    const activeLabel = effectiveActiveTab === 'users'
        ? 'Nhân sự'
        : effectiveActiveTab === 'folders'
            ? 'Thư mục'
            : 'Tài liệu';
    const activeCount = tabs.find((tab) => tab.id === effectiveActiveTab)?.count || 0;

    const deniedMessage = effectiveActiveTab === 'users'
        ? 'Bạn cần quyền user_read để xem nhân sự của phòng ban.'
        : effectiveActiveTab === 'folders'
            ? 'Bạn cần quyền folder_read và document_read để xem thư mục của phòng ban.'
            : 'Bạn cần quyền document_read để xem tài liệu của phòng ban.';

    return (
        <div className="space-y-4">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2">
                <div className="flex items-baseline gap-2">
                    <h2 className="text-xl font-black text-[#0d1c2e] tracking-tight">
                        Danh sách {activeLabel}
                    </h2>
                    <span className="text-lg font-bold text-slate-400">
                        ({activeCount})
                    </span>
                </div>
            </div>

            {tabs.length > 0 && (
                <div className="flex gap-1 p-1 bg-[#f8f9ff] rounded-xl w-fit">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => onTabChange(tab.id)}
                            className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${effectiveActiveTab === tab.id
                                ? 'bg-white text-[#9d4300] shadow-sm ring-1 ring-[#e0c0b1]/10'
                                : 'text-slate-400 hover:text-slate-600'
                                }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            )}

            <div className="bg-white rounded-2xl p-4 shadow-sm border border-[#e0c0b1]/20">
                {!effectiveActiveTab ? (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm font-medium text-amber-700">
                        Bạn cần thêm quyền user_read, folder_read hoặc document_read để xem dữ liệu mở rộng của phòng ban.
                    </div>
                ) : effectiveActiveTab === 'users' && canViewUsers ? (
                    <StaffUsersTab
                        deptId={deptId}
                        initialData={departmentDetail.users}
                    />
                ) : effectiveActiveTab === 'folders' && canViewFolders ? (
                    <StaffFoldersTab deptId={deptId} />
                ) : effectiveActiveTab === 'documents' && canViewDocuments ? (
                    <StaffDocumentsTab
                        deptId={deptId}
                        initialData={departmentDetail.documents}
                    />
                ) : (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm font-medium text-amber-700">
                        {deniedMessage}
                    </div>
                )}
            </div>
        </div>
    );
}
