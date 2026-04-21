/**
 * Staff Folders Tab
 * Displays paginated list of department folders
 * API: GET /api/v1/departments/{id}/folders?page=1&page_size=10
 */

'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useDepartmentFolders } from '@/hooks/departments/useDepartmentDetail';
import Pagination from '@/components/common/Pagination';
import TabLoading from '@/components/departments/loading/TabLoading';
import { FolderDetail } from '@/types/folders';
import { PaginatedResponse } from '@/types/departments';

interface StaffFoldersTabProps {
    deptId: string;
    initialData?: PaginatedResponse<FolderDetail>;
}

export default function StaffFoldersTab({ deptId, initialData }: StaffFoldersTabProps) {
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(10);

    // API Hook: Fetch folders with pagination
    const hookResult = useDepartmentFolders(
        page === 1 && initialData ? '' : deptId,
        page,
        pageSize
    );

    // Combine local hook data with initial data
    const data = page === 1 && initialData ? initialData : hookResult.data;
    const loading = page === 1 && initialData ? false : hookResult.loading;
    const error = hookResult.error;

    if (loading) {
        return <TabLoading />;
    }

    if (error) {
        return (
            <div className="p-6 bg-error-container rounded-lg text-error">
                <p className="font-medium">Lỗi tải danh sách thư mục</p>
                <p className="text-sm mt-1">{error}</p>
            </div>
        );
    }

    if (!data?.items || data.items.length === 0) {
        return (
            <div className="p-6 text-center text-on-surface-variant">
                Không có thư mục nào trong phòng ban
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Folders Table */}
            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                    <thead className="border-b border-outline-variant bg-surface-container-low">
                        <tr>
                            <th className="px-4 py-3 font-semibold text-on-surface">Tên thư mục</th>
                            <th className="px-4 py-3 font-semibold text-on-surface">Phạm vi truy cập</th>
                            <th className="px-4 py-3 font-semibold text-on-surface text-center">Tài liệu</th>
                            <th className="px-4 py-3 font-semibold text-on-surface text-center">Thư mục con</th>
                            <th className="px-4 py-3 font-semibold text-on-surface">Hành động</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-outline-variant">
                        {data.items.map((folder: FolderDetail) => (
                            <tr
                                key={folder.id}
                                className="hover:bg-surface-container-low transition-colors"
                            >
                                <td className="px-4 py-3">
                                    <div className="flex items-center gap-2">
                                        <span className="text-lg">📁</span>
                                        <span className="font-medium text-on-surface">{folder.name}</span>
                                    </div>
                                </td>
                                <td className="px-4 py-3">
                                    <span
                                        className={`px-2 py-1 rounded text-label-md font-medium ${folder.access_scope === 'PRIVATE'
                                                ? 'bg-error-container text-error'
                                                : 'bg-primary-fixed text-on-primary-fixed'
                                            }`}
                                    >
                                        {folder.access_scope === 'PRIVATE' ? '🔒 Riêng tư' : '👥 Công khai'}
                                    </span>
                                </td>
                                <td className="px-4 py-3 text-center">
                                    <span className="inline-block bg-surface-container-highest px-2 py-1 rounded">
                                        {folder.document_count || 0}
                                    </span>
                                </td>
                                <td className="px-4 py-3 text-center">
                                    <span className="inline-block bg-surface-container-highest px-2 py-1 rounded">
                                        {folder.subfolder_count || 0}
                                    </span>
                                </td>
                                <td className="px-4 py-3">
                                    <Link
                                        href={`/dashboard/folders/${folder.id}`}
                                        className="text-primary hover:underline font-medium"
                                    >
                                        Xem chi tiết →
                                    </Link>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {data.pagination && (
                <Pagination
                    currentPage={data.pagination.page}
                    totalPages={data.pagination.total_pages}
                    pageSize={pageSize}
                    onPageChange={setPage}
                    onPageSizeChange={setPageSize}
                />
            )}
        </div>
    );
}
