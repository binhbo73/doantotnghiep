/**
 * Staff Users Tab
 * Displays paginated list of department users in a table
 */

'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import { useDepartmentUsers } from '@/hooks/departments/useDepartmentDetail';
import Pagination from '@/components/common/Pagination';
import TabLoading from '@/components/departments/loading/TabLoading';
import { UserDetail, PaginatedResponse } from '@/types/departments';

interface StaffUsersTabProps {
    deptId: string;
    initialData?: PaginatedResponse<UserDetail>;
}

const POSITIONS = ['Senior Developer', 'Lead UX Researcher', 'Fullstack Engineer', 'Project Manager', 'QA Engineer', 'DevOps Specialist'];
const STATUSES = [
    { label: 'Đang làm việc', color: 'bg-[#e7f9ed] text-[#22c55e]' },
    { label: 'Trong cuộc họp', color: 'bg-[#fff7ed] text-[#f97316]' },
    { label: 'Ngoại tuyến', color: 'bg-[#f1f5f9] text-[#64748b]' }
];

export default function StaffUsersTab({ deptId, initialData }: StaffUsersTabProps) {
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(10);

    // API Hook: Fetch users with pagination
    // Only call hook if we're not on page 1 OR if initialData wasn't provided
    const hookResult = useDepartmentUsers(
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
            <div className="p-6 bg-red-50 rounded-2xl text-red-600 border border-red-100">
                <p className="font-bold">Lỗi tải danh sách nhân sự</p>
                <p className="text-sm mt-1">{error}</p>
            </div>
        );
    }

    if (!data?.items || data.items.length === 0) {
        return (
            <div className="p-12 text-center text-slate-400">
                <span className="material-symbols-outlined text-4xl mb-2 block">group_off</span>
                <p className="text-sm font-medium">Không có nhân sự trong phòng ban</p>
            </div>
        );
    }

    return (
        <div className="space-y-6 relative">
            <div className="overflow-x-auto">
                <table className="w-full text-left border-separate border-spacing-y-2">
                    <thead>
                        <tr className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">
                            <th className="px-4 py-3">Nhân viên</th>
                            <th className="px-4 py-3">Chức vụ</th>
                            <th className="px-4 py-3">Email</th>
                            <th className="px-4 py-3">Trạng thái</th>
                            <th className="px-4 py-3 text-right">Hành động</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.items.map((user: UserDetail, idx: number) => {
                            const position = POSITIONS[idx % POSITIONS.length];
                            const status = STATUSES[idx % STATUSES.length];
                            
                            return (
                                <tr key={user.id} className="group hover:bg-slate-50/50 transition-colors">
                                    <td className="px-4 py-4">
                                        <div className="flex items-center gap-4">
                                            {/* Avatar */}
                                            <div className="w-10 h-10 rounded-xl overflow-hidden flex-shrink-0 bg-slate-100 ring-2 ring-white shadow-sm">
                                                {user.avatar_url ? (
                                                    <Image
                                                        src={user.avatar_url}
                                                        alt={user.full_name}
                                                        width={40}
                                                        height={40}
                                                        className="w-full h-full object-cover"
                                                    />
                                                ) : (
                                                    <div className="w-full h-full bg-blue-50 flex items-center justify-center">
                                                        <span className="text-[10px] font-black text-blue-600">
                                                            {user.full_name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??'}
                                                        </span>
                                                    </div>
                                                )}
                                            </div>
                                            {/* Name & ID */}
                                            <div className="min-w-0">
                                                <p className="text-xs font-bold text-[#0d1c2e] group-hover:text-[#9d4300] transition-colors truncate">
                                                    {user.full_name}
                                                </p>
                                                <p className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter mt-0.5">
                                                    ID: #EMP-{user.id.substring(0, 3).toUpperCase()}
                                                </p>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-4 py-2">
                                        <span className="text-xs font-medium text-slate-600">{position}</span>
                                    </td>
                                    <td className="px-4 py-2">
                                        <span className="text-xs font-medium text-slate-500">{user.email}</span>
                                    </td>
                                    <td className="px-4 py-2">
                                        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-bold ${status.color}`}>
                                            <span className="w-1 h-1 rounded-full bg-current"></span>
                                            {status.label}
                                        </span>
                                    </td>
                                    <td className="px-4 py-2 text-right">
                                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-[#9d4300] hover:bg-white transition-all">
                                                <span className="material-symbols-outlined text-base">edit</span>
                                            </button>
                                            <button className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-red-500 hover:bg-white transition-all">
                                                <span className="material-symbols-outlined text-base">delete</span>
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {/* Floating Action Button (Matches Stitch UI) */}
            <button className="absolute -bottom-4 right-0 w-12 h-12 bg-[#9d4300] text-white rounded-2xl shadow-xl hover:scale-110 active:scale-95 transition-all flex items-center justify-center hover:shadow-[#9d4300]/50 z-10">
                <span className="material-symbols-outlined text-2xl font-black">person_add</span>
            </button>

            {/* Pagination */}
            {data.pagination && (
                <div className="pt-6 border-t border-slate-50">
                    <Pagination
                        currentPage={data.pagination.page}
                        totalPages={data.pagination.total_pages}
                        pageSize={pageSize}
                        onPageChange={setPage}
                        onPageSizeChange={setPageSize}
                    />
                </div>
            )}
        </div>
    );
}
