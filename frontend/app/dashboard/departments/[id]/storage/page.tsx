'use client'

/**
 * Department Storage Archive Page
 * Route: /dashboard/departments/[id]/storage
 * 
 * Displays the storage/archive tab for a department with folder tree
 * and document management functionality
 */



import React from 'react';
import { useParams } from 'next/navigation';
import { DepartmentStorageArchive } from '@/components/features/departments/storage';
import DepartmentDetailLayout from '@/components/departments/layout/DepartmentDetailLayout';
import { useDepartmentDetail } from '@/hooks/departments/useDepartmentDetail';
import LoadingSkeletons from '@/components/departments/loading/LoadingSkeletons';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import { useRBAC } from '@/hooks/useRBAC'

export default function DepartmentStoragePage() {
    const params = useParams();
    const deptId = params.id as string;
    const { hasPermission } = useRBAC()
    const canReadDepartment = hasPermission('department_read')
    const canReadFolders = hasPermission('folder_read')
    const canReadDocuments = hasPermission('document_read')
    const canAccess = canReadDepartment && canReadFolders && canReadDocuments

    const { data: departmentDetail, loading, error } = useDepartmentDetail(
        deptId,
        { enabled: canAccess }
    );

    if (!canAccess) {
        return (
            <div className="p-8 text-center text-amber-700 font-bold bg-amber-50 rounded-xl border border-amber-200">
                Bạn không có quyền xem kho lưu trữ của phòng ban này
            </div>
        );
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
        return (
            <div className="p-8 text-center text-red-500 font-bold">
                Phòng ban không tồn tại
            </div>
        );
    }

    return (
        <DepartmentDetailLayout deptId={deptId}>
            <DepartmentStorageArchive
                departmentId={deptId}
                departmentName={departmentDetail.name}
                canReadFolders={canReadFolders}
                canReadDocuments={canReadDocuments}
            />
        </DepartmentDetailLayout>
    );
}
