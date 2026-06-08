'use client';

import { AppIcon } from '@/components/ui/AppIcon'
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DepartmentNode } from '@/types/departments';

interface SubDepartmentsTreeSectionProps {
    subDepartments: DepartmentNode[];
}

/**
 * Recursive Tree Node Component
 * Displays a single department node with expandable children
 */
function TreeNode({
    dept,
    level = 0,
    onNavigate,
}: {
    dept: DepartmentNode;
    level?: number;
    onNavigate: (deptId: string) => void;
}) {
    const [isExpanded, setIsExpanded] = useState(level < 2); // Auto-expand first 2 levels
    const hasChildren = dept.sub_departments && dept.sub_departments.length > 0;

    const getIndentation = () => {
        return `${level * 1.5}rem`;
    };

    return (
        <div className="select-none">
            {/* Main Node */}
            <div
                className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-slate-50/80 transition-colors group"
                style={{ paddingLeft: getIndentation() }}
            >
                {/* Expand/Collapse Button */}
                <div className="w-5 flex items-center justify-center">
                    {hasChildren ? (
                        <button
                            onClick={() => setIsExpanded(!isExpanded)}
                            className="p-0.5 hover:bg-slate-200 rounded transition-colors"
                            title={isExpanded ? 'Thu gọn' : 'Mở rộng'}
                        >
                            <AppIcon name="expand_more" className="text-lg transition-transform" />
                        </button>
                    ) : (
                        <div className="w-5 h-5" />
                    )}
                </div>

                {/* Department Icon & Info */}
                <div className="flex items-center gap-3 flex-1 min-w-0">
                    {/* Department Icon */}
                    <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#9d4300]/10 to-[#f97316]/10 flex items-center justify-center flex-shrink-0">
                        <AppIcon name="hub" className="text-sm text-[#9d4300]" />
                    </div>

                    {/* Department Name & Stats */}
                    <div className="flex-1 min-w-0">
                        <button
                            onClick={() => onNavigate(dept.id)}
                            className="text-sm font-semibold text-slate-900 hover:text-[#9d4300] transition-colors text-left truncate group-hover:underline"
                        >
                            {dept.name}
                        </button>
                        <div className="flex gap-4 text-[10px] text-slate-400">
                            <span className="flex items-center gap-1">
                                <AppIcon name="person" className="text-xs" />
                                {dept.member_count} nhân sự
                            </span>
                            {dept.folder_count > 0 && (
                                <span className="flex items-center gap-1">
                                    <AppIcon name="folder" className="text-xs" />
                                    {dept.folder_count} thư mục
                                </span>
                            )}
                            {dept.document_count > 0 && (
                                <span className="flex items-center gap-1">
                                    <AppIcon name="description" className="text-xs" />
                                    {dept.document_count} tài liệu
                                </span>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Children - Render recursively if expanded */}
            {hasChildren && isExpanded && (
                <div className="border-l-2 border-slate-200/50 ml-6">
                    {dept.sub_departments!.map((childDept) => (
                        <TreeNode
                            key={childDept.id}
                            dept={childDept}
                            level={level + 1}
                            onNavigate={onNavigate}
                        />
                    ))}
                </div>
            )}

            {/* Collapsed indicator */}
            {hasChildren && !isExpanded && (
                <div
                    className="text-[10px] text-slate-400 py-1 px-3 italic"
                    style={{ paddingLeft: getIndentation() }}
                >
                    +{dept.sub_departments!.length} phòng ban con
                </div>
            )}
        </div>
    );
}

/**
 * Sub-Departments Tree Section
 * Shows hierarchical tree of all sub-departments with expand/collapse
 */
export default function SubDepartmentsTreeSection({
    subDepartments,
}: SubDepartmentsTreeSectionProps) {
    const router = useRouter();
    const [expandAll, setExpandAll] = useState(false);

    const handleNavigate = (deptId: string) => {
        router.push(`/dashboard/departments/${deptId}`);
    };

    // Count total departments recursively
    const countTotal = (depts: DepartmentNode[]): number => {
        return depts.reduce((sum, dept) => {
            return sum + 1 + (dept.sub_departments ? countTotal(dept.sub_departments) : 0);
        }, 0);
    };

    const totalDepts = countTotal(subDepartments);

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <AppIcon name="schema" className="text-[#9d4300] text-lg" />
                    <h2 className="text-base font-black text-[#0d1c2e] tracking-tight">
                        Cây phòng ban ({totalDepts})
                    </h2>
                </div>

                {/* Expand/Collapse All Button */}
                {totalDepts > 3 && (
                    <button
                        onClick={() => setExpandAll(!expandAll)}
                        className="text-[11px] font-semibold text-[#9d4300] hover:text-[#7a3300] transition-colors px-2 py-1 rounded hover:bg-orange-50 flex items-center gap-1"
                    >
                        <AppIcon name={expandAll ? 'unfold_less' : 'unfold_more'} className="text-sm" />
                        {expandAll ? 'Thu gọn tất cả' : 'Mở rộng tất cả'}
                    </button>
                )}
            </div>

            {/* Tree */}
            <div className="bg-white rounded-xl border border-[#e0c0b1]/30 p-4 space-y-1">
                {subDepartments.length === 0 ? (
                    <div className="text-center py-8 text-slate-400">
                        <AppIcon name="folder_off" className="text-3xl opacity-30 block mb-2" />
                        <p className="text-sm">Không có phòng ban con</p>
                    </div>
                ) : (
                    subDepartments.map((dept) => (
                        <TreeNode
                            key={dept.id}
                            dept={dept}
                            level={0}
                            onNavigate={handleNavigate}
                        />
                    ))
                )}
            </div>

            {/* Info Footer */}
            <div className="text-[10px] text-slate-400 px-4">
                💡 Nhấp vào tên phòng ban để xem chi tiết. Nhấp vào mũi tên để mở rộng/thu gọn.
            </div>
        </div>
    );
}
