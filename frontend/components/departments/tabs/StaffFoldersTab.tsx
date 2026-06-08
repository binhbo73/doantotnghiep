'use client'

import { AppIcon } from '@/components/ui/AppIcon'
/**
 * Staff Folders Tab
 * Displays department folders in a pure tree structure (folders only)
 */



import React from 'react';
import { useDepartmentFolders, FolderTreeNode } from '@/hooks/departments/useDepartmentFolders';
import TabLoading from '@/components/departments/loading/TabLoading';
import Link from 'next/link';
import { useRBAC } from '@/hooks/useRBAC';

interface StaffFoldersTabProps {
    deptId: string;
}

export default function StaffFoldersTab({ deptId }: StaffFoldersTabProps) {
    const { hasPermission } = useRBAC();
    const canReadFolders = hasPermission('folder_read');
    const canReadDocuments = hasPermission('document_read');
    const canAccess = canReadFolders && canReadDocuments;

    // API Hook: Fetch folders in tree structure
    const { folders, loading, error, toggleFolder } = useDepartmentFolders(deptId, {
        enabled: canAccess,
        canReadFolders,
        canReadDocuments,
    });

    if (!canAccess) {
        return (
            <div className="p-6 bg-amber-50 rounded-lg text-amber-700 border border-amber-200">
                Bạn cần quyền folder_read và document_read để xem cây thư mục phòng ban.
            </div>
        );
    }

    if (loading) {
        return <TabLoading />;
    }

    if (error) {
        return (
            <div className="p-6 bg-error-container rounded-lg text-error border border-error/20">
                <p className="font-medium flex items-center gap-2">
                    <AppIcon name="error" className="" />
                    Lỗi tải danh sách thư mục
                </p>
                <p className="text-sm mt-1 ml-7">{error}</p>
            </div>
        );
    }

    if (!folders || folders.length === 0) {
        return (
            <div className="p-12 text-center bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200">
                <div className="w-16 h-16 bg-white rounded-2xl shadow-sm flex items-center justify-center mx-auto mb-4">
                    <AppIcon name="folder_off" className="text-3xl text-slate-300" />
                </div>
                <p className="text-slate-500 font-medium italic text-sm">
                    Không có thư mục nào trong phòng ban này
                </p>
            </div>
        );
    }

    const renderFolderNode = (node: FolderTreeNode, depth: number = 0): React.ReactNode => {
        const hasChildren = (node.subFolders && node.subFolders.length > 0) || ((node.subfolder_count || 0) > 0);
        const isExpanded = node.expanded;

        return (
            <div key={node.id} className="relative">
                {/* Horizontal connector line from parent */}
                {depth > 0 && (
                    <div className="absolute left-[-28px] top-[24px] w-7 h-px bg-amber-200"></div>
                )}

                {/* Folder Item Row */}
                <div
                    onClick={() => hasChildren && toggleFolder(node.id)}
                    className={`group flex items-center gap-3 p-3 rounded-2xl cursor-pointer transition-all ${isExpanded
                        ? 'bg-amber-50 shadow-sm ring-1 ring-amber-200'
                        : 'hover:bg-slate-50'
                        }`}
                >
                    {/* Expand/Collapse Chevron */}
                    <div className={`w-6 h-6 flex items-center justify-center transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}>
                        {hasChildren ? (
                            <AppIcon name="chevron_right" className={`text-xl ${isExpanded ? 'text-amber-600' : 'text-slate-400'}`} />
                        ) : (
                            <div className="w-1.5 h-1.5 rounded-full bg-slate-200 ml-1"></div>
                        )}
                    </div>

                    {/* Folder Icon */}
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-sm ${isExpanded ? 'bg-amber-500 text-white' : 'bg-amber-50 text-amber-600'
                        }`}>
                        <AppIcon name={isExpanded ? 'folder_open' : 'folder'} className="text-2xl" />
                    </div>

                    {/* Folder Details */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <h3 className={`text-sm font-black truncate ${isExpanded ? 'text-amber-700' : 'text-[#0d1c2e]'}`}>
                                {node.name}
                            </h3>
                            {node.access_scope === 'personal' && (
                                <AppIcon name="lock" className="text-xs text-red-400" />
                            )}
                        </div>
                        {node.description && (
                            <p className="text-[11px] text-slate-400 font-medium truncate mt-0.5">
                                {node.description}
                            </p>
                        )}
                    </div>

                    {/* Badge Stats on the Right */}
                    <div className="flex items-center gap-2">
                        {/* Subfolder Badge */}
                        {node.subfolder_count !== undefined && node.subfolder_count > 0 && (
                            <div className="flex items-center gap-1 px-2.5 py-1.5 bg-amber-50 rounded-xl border border-amber-200 text-amber-600">
                                <AppIcon name="folder_zip" className="text-lg" />
                                <span className="text-xs font-black">{node.subfolder_count}</span>
                            </div>
                        )}

                        {/* Document Badge */}
                        <div className="flex items-center gap-1 px-2.5 py-1.5 bg-slate-50 rounded-xl border border-slate-100 text-slate-500">
                            <AppIcon name="description" className="text-lg" />
                            <span className="text-xs font-black">{node.document_count || 0}</span>
                        </div>

                        {/* Link to detail */}
                        <Link
                            href={`/dashboard/folders/${node.id}`}
                            onClick={(e) => e.stopPropagation()}
                            className="w-9 h-9 flex items-center justify-center rounded-xl bg-white border border-amber-200 text-slate-400 hover:text-amber-600 hover:border-amber-600 transition-all ml-1 shadow-sm"
                        >
                            <AppIcon name="open_in_new" className="text-xl" />
                        </Link>
                    </div>
                </div>

                {/* Recursive Sub-folders */}
                {isExpanded && hasChildren && (
                    <div className={`${depth === 0 ? 'ml-10' : 'ml-8'} mt-2 space-y-2 relative`}>
                        {/* Vertical line connector */}
                        <div className="absolute left-[-28px] top-[-12px] w-px h-[calc(100%-12px)] bg-amber-200"></div>
                        {node.subFolders.map(child => renderFolderNode(child, depth + 1))}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="p-1 space-y-2">
            {folders.map(folder => renderFolderNode(folder, 0))}
        </div>
    );
}

