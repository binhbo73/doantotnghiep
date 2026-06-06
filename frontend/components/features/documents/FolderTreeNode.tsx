'use client'

import React from 'react'
import { Trash2 } from 'lucide-react'
import { FolderTreeNode } from '@/hooks/useDocumentStore'
import { FolderDocumentResponse, FolderResponse } from '@/services/folder'
import { DocumentRow } from './DocumentRow'
import { useRBAC } from '@/hooks/useRBAC'

interface FolderTreeNodeProps {
    node: FolderTreeNode
    depth: number
    selectedDocId: string | null
    onToggleFolder: (folderId: string) => void
    onSelectDocument: (doc: FolderDocumentResponse, folder: FolderResponse) => void
    onDeleteFolder?: (folder: FolderResponse) => void
    deletingFolderId?: string | null
    searchQuery?: string
    departmentMap?: Record<string, string>
    showPersonal?: boolean
}
// ─── Helper: Match search query ────────────────────────────

function matchesSearch(text: string, query: string): boolean {
    if (!query) return true
    return text.toLowerCase().includes(query.toLowerCase())
}

// ─── Folder Icon based on name ─────────────────────────────

function getFolderIcon(name: string, isExpanded: boolean): { icon: string; color: string; bg: string } {
    return {
        icon: isExpanded ? 'folder_open' : 'folder',
        color: 'text-amber-600',
        bg: 'bg-amber-50',
    }
}

function toSafeCount(primary: number | undefined, fallback: number | undefined): number {
    const primaryCount = Number(primary)
    if (Number.isFinite(primaryCount) && primaryCount > 0) {
        return primaryCount
    }

    const fallbackCount = Number(fallback)
    if (Number.isFinite(fallbackCount) && fallbackCount > 0) {
        return fallbackCount
    }

    return 0
}

// ─── Scope Badge Component ───────────────────────────────────

export function ScopeBadge({ scope }: { scope: string }) {
    const config = {
        company: { icon: 'corporate_fare', color: 'text-blue-600 bg-blue-50 border-blue-100', label: 'Công ty' },
        department: { icon: 'group', color: 'text-purple-600 bg-purple-50 border-purple-100', label: 'Phòng ban' },
        personal: { icon: 'lock', color: 'text-slate-500 bg-slate-50 border-slate-200', label: 'Cá nhân' },
    }[scope as 'company' | 'department' | 'personal'] || { icon: 'folder', color: 'text-slate-400 bg-slate-50 border-slate-100', label: scope }

    return (
        <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-bold border ${config.color}`}>
            <span className="material-symbols-outlined text-[10px]">{config.icon}</span>
            {config.label}
        </span>
    )
}

export function FolderTreeNodeComponent({
    node,
    depth,
    selectedDocId,
    onToggleFolder,
    onSelectDocument,
    onDeleteFolder,
    deletingFolderId,
    searchQuery = '',
    departmentMap = {},
    showPersonal = true,
}: FolderTreeNodeProps) {
    const { folder, children, documents, isExpanded, isLoadingDocs, hasLoadedDocs } = node
    const { canWrite, hasPermission } = useRBAC()
    const folderPerm = folder.my_permission
    const canInspectFolderOwner = hasPermission('system_admin') || hasPermission('folder_update') || hasPermission('folder_delete')
    const canOpenFolder = hasPermission('folder_read')
    const canReadFolderDocuments = hasPermission('document_read')
    const canWriteFolder = hasPermission('folder_update') || canWrite(folderPerm)

    const folderIcon = getFolderIcon(folder.name, isExpanded)

    const restricted = !canOpenFolder

    // Filter documents by search
    const filteredDocs = searchQuery
        ? documents.filter((d) => matchesSearch(d.original_name || d.filename || '', searchQuery))
        : documents

    // Filter children by search (show if any child matches or any grandchild matches)
    const filteredChildren = searchQuery
        ? children.filter((child) => {
            if (matchesSearch(child.folder.name, searchQuery)) return true
            if (child.documents.some((d) => matchesSearch(d.original_name || d.filename || '', searchQuery))) return true
            return child.children.length > 0 // Keep parents if they might have matching grandchildren
        })
        : children

    // Hide this node if nothing matches the search query
    const folderMatches = matchesSearch(folder.name, searchQuery)
    const hasMatchingContent = filteredDocs.length > 0 || filteredChildren.length > 0
    if (searchQuery && !folderMatches && !hasMatchingContent) return null

    // Hide personal-scoped folders when showPersonal is false, except for system admins.
    if (folder.access_scope === 'personal' && !showPersonal && !hasPermission('system_admin')) return null

    const docCount = documents.length
    const subfolderCount = toSafeCount(children.length, folder.subfolder_count)
    const documentCount = toSafeCount(docCount, folder.document_count)

    return (
        <div className="relative">
            {/* Connector line from parent */}
            {depth > 0 && (
                <div className="absolute left-[-24px] top-[18px] w-6 h-px bg-amber-200"></div>
            )}

            {/* Folder Row */}
            <div
                onClick={!restricted ? () => onToggleFolder(folder.id) : undefined}
                className={`group flex items-center gap-2.5 px-3 py-2 rounded-xl ${restricted ? 'cursor-not-allowed opacity-90' : 'cursor-pointer'} transition-all duration-200 select-none ${isExpanded
                    ? 'bg-amber-50 border border-amber-200'
                    : 'hover:bg-white hover:shadow-sm border border-transparent'
                    }`}
            >
                {/* Expand/Collapse Chevron */}
                <span className={`material-symbols-outlined text-sm transition-transform duration-200 ${isExpanded ? 'rotate-90 text-amber-600' : 'text-slate-400'}`}>
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
                    <h3 className={`text-xs font-semibold truncate ${isExpanded ? 'text-amber-700' : 'text-slate-800'}`}>
                        {folder.name}
                    </h3>
                    {folder.description && (
                        <p className="text-[10px] text-slate-400 truncate mt-0.5 max-w-[200px]">
                            {folder.description}
                        </p>
                    )}
                    {/* Department badge */}
                    {folder.department_id && departmentMap[folder.department_id] && (
                        <div className="mt-1">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-50 text-[10px] rounded text-slate-500 border border-slate-100">
                                <span className="material-symbols-outlined text-[12px]">apartment</span>
                                <span className="truncate max-w-[140px]">{departmentMap[folder.department_id]}</span>
                            </span>
                        </div>
                    )}

                    {/* Scope Badge */}
                    <div className="flex items-center gap-1 mt-1">
                        <ScopeBadge scope={folder.access_scope} />
                        {/* If folder is personal, show owner/uploader name to users who can manage folders. */}
                        {folder.access_scope === 'personal' && folder.uploader_name && canInspectFolderOwner && (
                            <span className="ml-2 text-[10px] bg-yellow-50 px-2 py-0.5 rounded text-yellow-700 border border-yellow-100">{folder.uploader_name}</span>
                        )}
                    </div>
                </div>

                {/* Counts Badges */}
                <div className="flex items-center gap-1.5 ml-auto">
                    {onDeleteFolder && (
                        <button
                            type="button"
                            disabled={deletingFolderId === folder.id}
                            onClick={(event) => {
                                event.stopPropagation()
                                onDeleteFolder(folder)
                            }}
                            className="flex h-7 w-7 items-center justify-center rounded-md text-slate-400 opacity-0 transition-all hover:bg-red-50 hover:text-red-600 group-hover:opacity-100 focus:opacity-100 disabled:cursor-wait disabled:opacity-50"
                            title="Xóa thư mục"
                            aria-label={`Xóa thư mục ${folder.name}`}
                        >
                            <Trash2 size={15} aria-hidden="true" />
                        </button>
                    )}

                    {/* Sub-folder Count */}
                    {subfolderCount > 0 && (
                        <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-blue-50 rounded-md text-[10px] font-bold text-blue-600 border border-blue-100">
                            <span className="material-symbols-outlined text-[10px]">folder_zip</span>
                            {subfolderCount}
                        </span>
                    )}

                    {/* Document Count */}
                    {documentCount > 0 && (
                        <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-slate-100 rounded-md text-[10px] font-medium text-slate-500 border border-slate-200">
                            <span className="material-symbols-outlined text-[10px]">description</span>
                            {documentCount}
                        </span>
                    )}
                </div>

                {/* Loading indicator */}
                {isLoadingDocs && (
                    <div className="w-4 h-4 border-2 border-amber-200 border-t-amber-600 rounded-full animate-spin" />
                )}
            </div>

            {/* Expanded Content */}
            {isExpanded && (() => {
                // FIXED: Check access_scope BEFORE checking department restrictions
                const restricted = !canOpenFolder

                if (restricted) {
                    return (
                        <div className={`${depth === 0 ? 'ml-8' : 'ml-6'} mt-1 relative`}>
                            <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                                <div className="flex flex-col items-center">
                                    <span className="material-symbols-outlined text-3xl text-slate-400 mb-2">lock</span>
                                    <p className="text-sm font-semibold">Quyền hạn giới hạn</p>
                                    <p className="text-xs text-slate-500 mt-1">Bạn chỉ có thể xem dữ liệu thư mục thuộc phòng ban của bạn.</p>
                                </div>
                            </div>
                        </div>
                    )
                }

                return (
                    <div className={`${depth === 0 ? 'ml-8' : 'ml-6'} mt-1 relative`}>
                        {/* Vertical connector line */}
                        {(filteredChildren.length > 0 || filteredDocs.length > 0) && (
                            <div className="absolute left-[-24px] top-0 w-px h-[calc(100%-16px)] bg-amber-200/60"></div>
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
                                    onDeleteFolder={onDeleteFolder}
                                    deletingFolderId={deletingFolderId}
                                    searchQuery={searchQuery}
                                    departmentMap={departmentMap}
                                    showPersonal={showPersonal}
                                />
                            ))}
                        </div>

                        {/* Document access locked */}
                        {!canReadFolderDocuments && documentCount > 0 && (
                            <div className="mt-2 rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-center">
                                <div className="flex flex-col items-center">
                                    <span className="material-symbols-outlined text-2xl text-slate-400 mb-1">lock</span>
                                    <p className="text-xs font-semibold text-slate-600">Tài liệu trong thư mục bị khóa</p>
                                    <p className="text-[10px] text-slate-400 mt-1">Bạn cần quyền document_read để xem tài liệu bên trong.</p>
                                </div>
                            </div>
                        )}

                        {/* Documents */}
                        {hasLoadedDocs && filteredDocs.length > 0 && (
                            <div className="mt-1 space-y-0.5">
                                {filteredDocs.map((doc) => (
                                    <div key={doc.id} className="relative">
                                        {/* Connector line */}
                                        <div className="absolute left-[-24px] top-[16px] w-6 h-px bg-amber-200/60"></div>
                                        <DocumentRow
                                            document={doc}
                                            isSelected={selectedDocId === doc.id}
                                            onSelect={() => onSelectDocument(doc, folder)}
                                            folderName={folder.name}
                                            departmentName={departmentMap[doc.department || doc.department_id || '']}
                                        />
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Empty state */}
                        {hasLoadedDocs && documents.length === 0 && children.length === 0 && !(documentCount > 0 && !canReadFolderDocuments) && (
                            <div className="flex flex-col items-center justify-center py-6 px-4 text-center">
                                <span className="material-symbols-outlined text-3xl text-slate-200 mb-2">folder_off</span>
                                <p className="text-[11px] text-slate-500 font-medium">Thư mục trống</p>
                                {canWriteFolder ? (
                                    <p className="text-[10px] text-slate-400 mt-1">Sẵn sàng để tải lên tài liệu mới</p>
                                ) : (
                                    <p className="text-[10px] text-slate-400 mt-1 italic">Bạn chỉ có quyền xem thư mục này</p>
                                )}
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
                )
            })()}
        </div>
    )
}
