/**
 * Department Detail Page
 * Route: /dashboard/departments/[id]
 * 
 * Main page component that orchestrates all department detail views
 * Uses Hybrid Approach APIs to fetch and display data
 */

'use client';

import { useParams } from 'next/navigation';
import { useState } from 'react';
import DepartmentDetailLayout from '@/components/departments/layout/DepartmentDetailLayout';
import DepartmentDetailHeader from '@/components/departments/sections/DepartmentDetailHeader';
import ManagerCard from '@/components/departments/sections/ManagerCard';
import SubDepartmentsSection from '@/components/departments/sections/SubDepartmentsSection';
import StaffTableSection from '@/components/departments/sections/StaffTableSection';
// import InfoCardsSection from '@/components/departments/sections/InfoCardsSection';
import LoadingSkeletons from '@/components/departments/loading/LoadingSkeletons';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import { useDepartmentDetail } from '@/hooks/departments/useDepartmentDetail';

export default function DepartmentDetailPage() {
    const params = useParams();
    const deptId = params.id as string;

    const [activeTab, setActiveTab] = useState<'users' | 'folders' | 'documents'>('users');

    // API Hook: Fetch department detail with counts
    const {
        data: departmentDetail,
        loading,
        error,
    } = useDepartmentDetail(deptId);

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
                        <SubDepartmentsSection
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
