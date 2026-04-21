/**
 * Staff Documents Tab
 * Displays paginated list of department documents
 * API: GET /api/v1/departments/{id}/documents?page=1&page_size=10
 */

'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useDepartmentDocuments } from '@/hooks/departments/useDepartmentDetail';
import Pagination from '@/components/common/Pagination';
import TabLoading from '@/components/departments/loading/TabLoading';
import { DocumentDetail } from '@/types/documents';
import { PaginatedResponse } from '@/types/departments';

interface StaffDocumentsTabProps {
    deptId: string;
    initialData?: PaginatedResponse<DocumentDetail>;
}

export default function StaffDocumentsTab({ deptId, initialData }: StaffDocumentsTabProps) {
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(10);

    // API Hook: Fetch documents with pagination
    const hookResult = useDepartmentDocuments(
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
                <p className="font-medium">Lỗi tải danh sách tài liệu</p>
                <p className="text-sm mt-1">{error}</p>
            </div>
        );
    }

    if (!data?.items || data.items.length === 0) {
        return (
            <div className="p-6 text-center text-on-surface-variant">
                Không có tài liệu nào trong phòng ban
            </div>
        );
    }

    const getFileIcon = (fileType: string) => {
        const type = fileType?.toLowerCase() || '';
        if (type.includes('pdf')) return '📕';
        if (type.includes('word') || type.includes('doc')) return '📗';
        if (type.includes('sheet') || type.includes('xls')) return '📊';
        if (type.includes('slide') || type.includes('ppt')) return '🎨';
        if (type.includes('image')) return '🖼️';
        return '📄';
    };

    const formatFileSize = (bytes: number) => {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    };

    const getStatusBadge = (status: string) => {
        const statusMap: Record<string, { label: string; color: string }> = {
            DRAFT: { label: '⏳ Nháp', color: 'bg-secondary-container text-on-secondary-container' },
            ACTIVE: { label: '✓ Hoạt động', color: 'bg-primary-fixed text-on-primary-fixed' },
            ARCHIVED: { label: '📦 Lưu trữ', color: 'bg-surface-container-high text-on-surface' },
            DELETED: { label: '🗑️ Đã xóa', color: 'bg-error-container text-error' },
        };
        const info = statusMap[status] || statusMap['ACTIVE'];
        return <span className={`px-2 py-1 rounded text-label-md font-medium ${info.color}`}>{info.label}</span>;
    };

    return (
        <div className="space-y-4">
            {/* Documents Table */}
            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                    <thead className="border-b border-outline-variant bg-surface-container-low">
                        <tr>
                            <th className="px-4 py-3 font-semibold text-on-surface">Tên tài liệu</th>
                            <th className="px-4 py-3 font-semibold text-on-surface">Loại</th>
                            <th className="px-4 py-3 font-semibold text-on-surface text-right">Kích thước</th>
                            <th className="px-4 py-3 font-semibold text-on-surface">Trạng thái</th>
                            <th className="px-4 py-3 font-semibold text-on-surface">Hành động</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-outline-variant">
                        {data.items.map((doc: DocumentDetail) => (
                            <tr
                                key={doc.id}
                                className="hover:bg-surface-container-low transition-colors"
                            >
                                <td className="px-4 py-3">
                                    <div className="flex items-center gap-2">
                                        <span className="text-lg">
                                            {getFileIcon(doc.file_type)}
                                        </span>
                                        <span className="font-medium text-on-surface truncate">
                                            {doc.filename}
                                        </span>
                                    </div>
                                </td>
                                <td className="px-4 py-3">
                                    <span className="text-on-surface-variant text-sm">
                                        {doc.file_type || 'Unknown'}
                                    </span>
                                </td>
                                <td className="px-4 py-3 text-right">
                                    <span className="text-on-surface-variant">
                                        {formatFileSize(doc.file_size)}
                                    </span>
                                </td>
                                <td className="px-4 py-3">
                                    {getStatusBadge(doc.status)}
                                </td>
                                <td className="px-4 py-3">
                                    <Link
                                        href={`/dashboard/documents/${doc.id}`}
                                        className="text-primary hover:underline font-medium"
                                    >
                                        Mở →
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
