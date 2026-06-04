/**
 * Department Detail Page
 * Route: /dashboard/departments/[id]
 * 
 * Main page component that orchestrates all department detail views
 * Uses Hybrid Approach APIs to fetch and display data
 */

'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useRBAC } from '@/hooks/useRBAC'
import DepartmentDetailLayout from '@/components/departments/layout/DepartmentDetailLayout';
import DepartmentDetailHeader from '@/components/departments/sections/DepartmentDetailHeader';
import ManagerCard from '@/components/departments/sections/ManagerCard';
import SubDepartmentsTreeSection from '@/components/departments/sections/SubDepartmentsTreeSection';
import StaffTableSection from '@/components/departments/sections/StaffTableSection';
// import InfoCardsSection from '@/components/departments/sections/InfoCardsSection';
import LoadingSkeletons from '@/components/departments/loading/LoadingSkeletons';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import { useDepartmentDetail } from '@/hooks/departments/useDepartmentDetail';

export default function DepartmentDetailPage() {
    const params = useParams();
    const deptId = params.id as string;

    const { hasPermission } = useRBAC()
    const canReadDepartment = hasPermission('department_read')
    const canReadUsers = hasPermission('user_read')
    const canReadFolders = hasPermission('folder_read')
    const canReadDocuments = hasPermission('document_read')

    const [activeTab, setActiveTab] = useState<'users' | 'folders' | 'documents'>('users');
    const expand = [
        canReadUsers ? 'users' as const : null,
        canReadFolders && canReadDocuments ? 'folders' as const : null,
        canReadDocuments ? 'documents' as const : null,
    ].filter(Boolean) as Array<'users' | 'folders' | 'documents'>;

    // API Hook: Fetch department detail with counts
    const {
        data: departmentDetail,
        loading,
        error,
    } = useDepartmentDetail(deptId, { enabled: canReadDepartment, expand });

    const canAccessDepartment = canReadDepartment

    // RBAC: backend permissions decide whether this page is visible.
    if (!canAccessDepartment) {
        return (
            <div className="min-h-screen flex items-center justify-center p-6">
                <div className="text-center max-w-lg bg-white rounded-2xl p-8 shadow-sm border">
                    <div className="w-16 h-16 rounded-full bg-slate-50 flex items-center justify-center mx-auto mb-4">
                        <span className="material-symbols-outlined text-3xl text-slate-400">lock</span>
                    </div>
                    <h3 className="text-lg font-bold mb-2">Quyền truy cập bị giới hạn</h3>
                    <p className="text-sm text-slate-500 mb-4">Bạn chỉ có thể xem chi tiết phòng ban mình quản lý hoặc phòng ban trực thuộc nó.</p>
                    <button onClick={() => window.history.back()} className="px-4 py-2 rounded bg-[#9d4300] text-white">Quay lại</button>
                </div>
            </div>
        )
    }

    if (loading) {
        return <LoadingSkeletons />;
    }

    if (error) {
        return (
            <ErrorBoundary
                error={error}
                onRetry={() => window.location.reload()}
            />
        );
    }

    if (!departmentDetail) {
        return <div className="p-8 text-center text-red-500 font-bold">Phòng ban không tồn tại</div>;
    }

    return (
        <DepartmentDetailLayout deptId={deptId}>
            <div className="space-y-12">
                {/* 1. Header (Full Width) */}
                <DepartmentDetailHeader
                    department={departmentDetail}
                    deptId={deptId}
                />

                {/* 2. Top Grid: Manager & Sub-departments */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                    {/* Left: Manager Card (Col 4) */}
                    <div className="lg:col-span-4">
                        <ManagerCard
                            manager={departmentDetail.manager}
                            deptId={deptId}
                        />
                    </div>

                    {/* Right: Sub-departments (Col 8) */}
                    <div className="lg:col-span-8 bg-[#eff4ff]/30 rounded-[2.5rem] p-8 border border-[#eff4ff] self-stretch">
                        <SubDepartmentsTreeSection
                            subDepartments={departmentDetail.sub_departments || []}
                        />
                    </div>
                </div>

                {/* 3. Staff Table (Full Width) */}
                <StaffTableSection
                    deptId={deptId}
                    activeTab={activeTab}
                    onTabChange={setActiveTab}
                    departmentDetail={departmentDetail}
                />


            </div>
        </DepartmentDetailLayout>
    );
}
