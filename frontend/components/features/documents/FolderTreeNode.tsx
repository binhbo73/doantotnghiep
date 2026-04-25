'use client'

import React from 'react'
import { FolderTreeNode } from '@/hooks/useDocumentStore'
import { FolderDocumentResponse, FolderResponse } from '@/services/folder'
import { DocumentRow } from './DocumentRow'

interface FolderTreeNodeProps {
    node: FolderTreeNode
    depth: number
    selectedDocId: string | null
    onToggleFolder: (folderId: string) => void
    onSelectDocument: (doc: FolderDocumentResponse, folder: FolderResponse) => void
    searchQuery?: string
}

// ─── Helper: Match search query ────────────────────────────

function matchesSearch(text: string, query: string): boolean {
    if (!query) return true
    return text.toLowerCase().includes(query.toLowerCase())
}

// ─── Folder Icon based on name ─────────────────────────────

function getFolderIcon(name: string, isExpanded: boolean): { icon: string; color: string; bg: string } {
    const n = name.toLowerCase()
    if (n.includes('sop') || n.includes('quy trình')) return { icon: 'rule_folder', color: 'text-emerald-600', bg: 'bg-emerald-50' }
    if (n.includes('dự án') || n.includes('project')) return { icon: 'work', color: 'text-violet-600', bg: 'bg-violet-50' }
    if (n.includes('thiết kế') || n.includes('design')) return { icon: 'design_services', color: 'text-pink-600', bg: 'bg-pink-50' }
    if (n.includes('kỹ thuật') || n.includes('technical') || n.includes('hệ thống')) return { icon: 'engineering', color: 'text-blue-600', bg: 'bg-blue-50' }
    if (n.includes('nhân sự') || n.includes('hr')) return { icon: 'group', color: 'text-teal-600', bg: 'bg-teal-50' }
    if (n.includes('tài chính') || n.includes('finance')) return { icon: 'payments', color: 'text-amber-600', bg: 'bg-amber-50' }
    if (n.includes('báo cáo') || n.includes('report')) return { icon: 'assessment', color: 'text-indigo-600', bg: 'bg-indigo-50' }

    return {
        icon: isExpanded ? 'folder_open' : 'folder',
        color: 'text-[#9d4300]',
        bg: 'bg-[#fff3e0]',
    }
}

export function FolderTreeNodeComponent({
    node,
    depth,
    selectedDocId,
    onToggleFolder,
    onSelectDocument,
    searchQuery = '',
}: FolderTreeNodeProps) {
    const { folder, children, documents, isExpanded, isLoadingDocs, hasLoadedDocs } = node
    const folderIcon = getFolderIcon(folder.name, isExpanded)

    // Filter documents by search
    const filteredDocs = searchQuery
        ? documents.filter((d) => matchesSearch(d.original_name || d.filename, searchQuery))
        : documents

    // Filter children by search (show if any child matches or any grandchild matches)
    const filteredChildren = searchQuery
        ? children.filter((child) => {
            if (matchesSearch(child.folder.name, searchQuery)) return true
            if (child.documents.some((d) => matchesSearch(d.original_name || d.filename, searchQuery))) return true
            return child.children.length > 0 // Keep parents if they might have matching grandchildren
        })
        : children

    // Hide this node if nothing matches the search query
    const folderMatches = matchesSearch(folder.name, searchQuery)
    const hasMatchingContent = filteredDocs.length > 0 || filteredChildren.length > 0
    if (searchQuery && !folderMatches && !hasMatchingContent) return null

    const hasContent = children.length > 0 || (hasLoadedDocs && documents.length > 0)
    const docCount = documents.length

    return (
        <div className="relative">
            {/* Connector line from parent */}
            {depth > 0 && (
                <div className="absolute left-[-24px] top-[18px] w-6 h-px bg-[#e0c0b1]"></div>
            )}

            {/* Folder Row */}
            <div
                onClick={() => onToggleFolder(folder.id)}
                className={`group flex items-center gap-2.5 px-3 py-2 rounded-xl cursor-pointer transition-all duration-200 select-none ${isExpanded
                        ? 'bg-[#fef5ed] border border-[#f97316]/20'
                        : 'hover:bg-white hover:shadow-sm border border-transparent'
                    }`}
            >
                {/* Expand/Collapse Chevron */}
                <span className={`material-symbols-outlined text-sm transition-transform duration-200 ${isExpanded ? 'rotate-90 text-[#9d4300]' : 'text-slate-400'}`}>
                    chevron_right
                </span>

                {/* Folder Icon */}
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${folderIcon.bg} ${folderIcon.color} transition-transform group-hover:scale-105`}>
                    <span className="material-symbols-outlined text-base" style={{ fontVariationSettings: "'FILL' 1" }}>
                        {folderIcon.icon}
                    </span>
                </div>

                {/* Folder Name */}
                <div className="flex-1 min-w-0">
                    <h3 className={`text-xs font-semibold truncate ${isExpanded ? 'text-[#9d4300]' : 'text-slate-800'}`}>
                        {folder.name}
                    </h3>
                    {folder.description && (
                        <p className="text-[10px] text-slate-400 truncate mt-0.5 max-w-[200px]">
                            {folder.description}
                        </p>
                    )}
                </div>

                {/* Counts Badges */}
                <div className="flex items-center gap-1.5 ml-auto">
                    {/* Sub-folder Count */}
                    {(children.length || folder.subfolder_count) > 0 && (
                        <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-blue-50 rounded-md text-[10px] font-bold text-blue-600 border border-blue-100">
                            <span className="material-symbols-outlined text-[10px]">folder_zip</span>
                            {children.length || folder.subfolder_count}
                        </span>
                    )}

                    {/* Document Count */}
                    {(docCount || folder.document_count) > 0 && (
                        <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-slate-100 rounded-md text-[10px] font-medium text-slate-500 border border-slate-200">
                            <span className="material-symbols-outlined text-[10px]">description</span>
                            {docCount || folder.document_count}
                        </span>
                    )}
                </div>

                {/* Loading indicator */}
                {isLoadingDocs && (
                    <div className="w-4 h-4 border-2 border-[#9d4300]/20 border-t-[#9d4300] rounded-full animate-spin" />
                )}
            </div>

            {/* Expanded Content */}
            {isExpanded && (
                <div className={`${depth === 0 ? 'ml-8' : 'ml-6'} mt-1 relative`}>
                    {/* Vertical connector line */}
                    {(filteredChildren.length > 0 || filteredDocs.length > 0) && (
                        <div className="absolute left-[-24px] top-0 w-px h-[calc(100%-16px)] bg-[#e0c0b1]/50"></div>
                    )}

                    {/* Sub-folders */}
                    <div className="space-y-1">
                        {filteredChildren.map((child) => (
                            <FolderTreeNodeComponent
                                key={child.folder.id}
                                node={child}
                                depth={depth + 1}
                                selectedDocId={selectedDocId}
                                onToggleFolder={onToggleFolder}
                                onSelectDocument={onSelectDocument}
                                searchQuery={searchQuery}
                            />
                        ))}
                    </div>

                    {/* Documents */}
                    {hasLoadedDocs && filteredDocs.length > 0 && (
                        <div className="mt-1 space-y-0.5">
                            {filteredDocs.map((doc) => (
                                <div key={doc.id} className="relative">
                                    {/* Connector line */}
                                    <div className="absolute left-[-24px] top-[16px] w-6 h-px bg-[#e0c0b1]/50"></div>
                                    <DocumentRow
                                        document={doc}
                                        isSelected={selectedDocId === doc.id}
                                        onSelect={() => onSelectDocument(doc, folder)}
                                    />
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Empty state */}
                    {hasLoadedDocs && documents.length === 0 && children.length === 0 && (
                        <div className="flex items-center gap-2 px-3 py-3 text-xs text-slate-400 italic">
                            <span className="material-symbols-outlined text-sm">folder_off</span>
                            Thư mục trống
                        </div>
                    )}

                    {/* Loading skeleton */}
                    {isLoadingDocs && (
                        <div className="space-y-2 px-3 py-2">
                            {[1, 2, 3].map((i) => (
                                <div key={i} className="flex items-center gap-3 animate-pulse">
                                    <div className="w-8 h-8 bg-slate-200 rounded-lg" />
                                    <div className="flex-1 space-y-1.5">
                                        <div className="h-3 bg-slate-200 rounded w-3/4" />
                                        <div className="h-2 bg-slate-100 rounded w-1/3" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
