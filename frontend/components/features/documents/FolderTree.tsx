'use client'

import React from 'react'
import { FolderTreeNode, OtherDocumentsNode } from '@/hooks/useDocumentStore'
import { FolderDocumentResponse, FolderResponse } from '@/services/folder'
import { FolderTreeNodeComponent } from './FolderTreeNode'
import { OtherDocuments } from './OtherDocuments'
import { useDepartmentOptions } from '@/hooks/useDepartmentOptions'
import { useMemo } from 'react'
import { useRBAC } from '@/hooks/useRBAC'

interface FolderTreeProps {
    tree: FolderTreeNode[]
    otherDocuments: OtherDocumentsNode
    selectedDocId: string | null
    onToggleFolder: (folderId: string) => void
    onToggleOtherDocuments: () => void
    onSelectDocument: (doc: FolderDocumentResponse, folder: FolderResponse) => void
    onDeleteFolder?: (folder: FolderResponse) => void
    deletingFolderId?: string | null
    searchQuery?: string
    showPersonal?: boolean
}

export function FolderTree({
    tree,
    otherDocuments,
    selectedDocId,
    onToggleFolder,
    onToggleOtherDocuments,
    onSelectDocument,
    onDeleteFolder,
    deletingFolderId,
    searchQuery = '',
    showPersonal = true,
}: FolderTreeProps) {
    // Load department list only when the current role can read departments.
    const { hasPermission } = useRBAC()
    const { data: departments } = useDepartmentOptions(hasPermission('department_read'))

    const departmentMap = useMemo(() => {
        const map: Record<string, string> = {}
        if (!departments) return map

        const recurse = (items: any[]) => {
            items.forEach((d) => {
                if (!d) return
                map[d.id] = d.name
                if (Array.isArray(d.sub_departments) && d.sub_departments.length > 0) {
                    recurse(d.sub_departments)
                }
            })
        }

        recurse(departments as any[])
        return map
    }, [departments])
    return (
        <div className="col-span-12 lg:col-span-7 bg-white shadow-sm ring-1 ring-slate-100 rounded-2xl overflow-hidden flex flex-col max-h-[85vh]">
            {/* Header */}
            <div className="flex justify-between items-center px-5 py-3.5 border-b border-slate-100 flex-shrink-0">
                <h2 className="text-sm font-bold flex items-center gap-2 text-slate-800">
                    <span className="material-symbols-outlined text-[#9d4300] text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>
                        account_tree
                    </span>
                    Cấu trúc Kho tài liệu
                </h2>

                <div className="flex items-center gap-1">
                    <button className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600 transition-colors" title="Thu gọn tất cả">
                        <span className="material-symbols-outlined text-base">unfold_less</span>
                    </button>
                    <button className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600 transition-colors" title="Làm mới">
                        <span className="material-symbols-outlined text-base">refresh</span>
                    </button>
                </div>
            </div>

            {/* Tree Content */}
            <div className="p-4 space-y-1.5 overflow-y-auto flex-1 scrollbar-thin scrollbar-thumb-slate-200 scrollbar-track-transparent">
                {tree.length > 0 || otherDocuments.departmentDocs.length > 0 || otherDocuments.personalDocs.length > 0 || otherDocuments.companyDocs.length > 0 ? (
                    <>
                        {/* Folder Tree */}
                        {tree.length > 0 && (
                            <div className="space-y-1.5">
                                {tree.map((node) => (
                                    <FolderTreeNodeComponent
                                        key={node.folder.id}
                                        node={node}
                                        depth={0}
                                        selectedDocId={selectedDocId}
                                        onToggleFolder={onToggleFolder}
                                        onSelectDocument={onSelectDocument}
                                        onDeleteFolder={onDeleteFolder}
                                        deletingFolderId={deletingFolderId}
                                        searchQuery={searchQuery}
                                        departmentMap={departmentMap}
                                        showPersonal={showPersonal}
                                    />
                                ))}
                            </div>
                        )}

                        {/* Other Documents Section */}
                        <OtherDocuments
                            otherDocuments={otherDocuments}
                            selectedDocId={selectedDocId}
                            onToggle={onToggleOtherDocuments}
                            onSelectDocument={(doc, folder) => onSelectDocument(doc, folder as any)}
                            searchQuery={searchQuery}
                            departmentMap={departmentMap}
                            showPersonal={showPersonal}
                        />
                    </>
                ) : (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                        <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
                            <span className="material-symbols-outlined text-3xl text-slate-300">folder_off</span>
                        </div>
                        <p className="text-sm font-medium text-slate-500 mb-1">Chưa có thư mục nào</p>
                        <p className="text-xs text-slate-400">Tạo thư mục mới để bắt đầu tổ chức tài liệu</p>
                    </div>
                )}
            </div>
        </div>
    )
}
