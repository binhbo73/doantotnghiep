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

    const getFileVisual = (fileType: string): { icon: string; color: string; bg: string } => {
        const type = fileType?.toLowerCase() || '';
        if (type.includes('pdf')) return { icon: 'picture_as_pdf', color: 'text-red-600', bg: 'bg-red-50' };
        if (type.includes('word') || type.includes('doc')) return { icon: 'article', color: 'text-blue-600', bg: 'bg-blue-50' };
        if (type.includes('sheet') || type.includes('xls') || type.includes('excel')) return { icon: 'table_chart', color: 'text-green-600', bg: 'bg-green-50' };
        if (type.includes('slide') || type.includes('ppt') || type.includes('presentation')) return { icon: 'slideshow', color: 'text-orange-600', bg: 'bg-orange-50' };
        if (type.includes('zip') || type.includes('rar') || type.includes('tar') || type.includes('gz')) return { icon: 'folder_zip', color: 'text-amber-600', bg: 'bg-amber-50' };
        if (type.includes('image') || type.includes('png') || type.includes('jpg') || type.includes('jpeg') || type.includes('gif') || type.includes('webp') || type.includes('svg')) return { icon: 'image', color: 'text-purple-600', bg: 'bg-purple-50' };
        return { icon: 'description', color: 'text-slate-500', bg: 'bg-slate-100' };
    };

    const formatFileSize = (bytes: number) => {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    };

    return (
        <div className="space-y-4">
            {/* Documents Table */}
            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                    <thead className="border-b border-slate-200 bg-slate-50">
                        <tr>
                            <th className="px-4 py-3 font-semibold text-slate-800">Tên tài liệu</th>
                            <th className="px-4 py-3 font-semibold text-slate-800">Loại</th>
                            <th className="px-4 py-3 font-semibold text-slate-800 text-right">Kích thước</th>
                            <th className="px-4 py-3 font-semibold text-slate-800">Hành động</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                        {data.items.map((doc: DocumentDetail) => (
                            <tr
                                key={doc.id}
                                className="hover:bg-amber-50 transition-colors"
                            >
                                <td className="px-4 py-3">
                                    <div className="flex items-center gap-2">
                                        {(() => {
                                            const fileVisual = getFileVisual(doc.file_type || '');
                                            return (
                                                <span className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${fileVisual.bg} ${fileVisual.color}`}>
                                                    <span className="material-symbols-outlined text-base">{fileVisual.icon}</span>
                                                </span>
                                            );
                                        })()}
                                        <span className="font-medium text-slate-900 whitespace-normal break-words">
                                            {doc.original_name}
                                        </span>
                                    </div>
                                </td>
                                <td className="px-4 py-3">
                                    <span className="text-slate-500 text-sm uppercase">
                                        {doc.file_type || 'Unknown'}
                                    </span>
                                </td>
                                <td className="px-4 py-3 text-right">
                                    <span className="text-slate-500">
                                        {formatFileSize(doc.file_size)}
                                    </span>
                                </td>
                                <td className="px-4 py-3">
                                    <Link
                                        href={`/dashboard/documents/${doc.id}`}
                                        className="text-amber-600 hover:underline font-medium"
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
