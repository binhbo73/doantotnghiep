'use client'

import React from 'react'
import { OtherDocumentsNode, FolderDocumentResponse } from '@/hooks/useDocumentStore'
import { FolderResponse } from '@/services/folder'
import { DocumentRow } from './DocumentRow'

interface OtherDocumentsProps {
    otherDocuments: OtherDocumentsNode
    selectedDocId: string | null
    onToggle: () => void
    onSelectDocument: (doc: FolderDocumentResponse, folder?: FolderResponse) => void
    searchQuery?: string
}

interface CategoryProps {
    title: string
    icon: string
    iconBg: string
    documents: FolderDocumentResponse[]
    selectedDocId: string | null
    onSelectDocument: (doc: FolderDocumentResponse) => void
    searchQuery?: string
}

// Category sub-component
function DocumentCategory({
    title,
    icon,
    iconBg,
    documents,
    selectedDocId,
    onSelectDocument,
    searchQuery = '',
}: CategoryProps) {
    // Filter documents based on search
    const filtered = documents.filter((doc) =>
        doc.original_name.toLowerCase().includes(searchQuery.toLowerCase())
    )

    if (filtered.length === 0) return null

    return (
        <div className="ml-4 border-l border-slate-200 pl-4 py-2">
            <div className="flex items-center gap-2 px-3 py-1.5 mb-1.5">
                <div className={`${iconBg} p-1.5 rounded`}>
                    <span className="material-symbols-outlined text-xs">{icon}</span>
                </div>
                <span className="text-xs font-semibold text-slate-600">{title}</span>
                <span className="ml-auto text-xs font-bold text-slate-400">{filtered.length}</span>
            </div>

            <div className="space-y-0.5">
                {filtered.map((doc) => (
                    <DocumentRow
                        key={doc.id}
                        document={doc}
                        isSelected={selectedDocId === doc.id}
                        onSelect={() => onSelectDocument(doc)}
                        depth={2}
                    />
                ))}
            </div>
        </div>
    )
}

export function OtherDocuments({
    otherDocuments,
    selectedDocId,
    onToggle,
    onSelectDocument,
    searchQuery = '',
}: OtherDocumentsProps) {
    const totalOtherDocs =
        otherDocuments.departmentDocs.length +
        otherDocuments.personalDocs.length +
        otherDocuments.companyDocs.length

    if (totalOtherDocs === 0) {
        return null
    }

    return (
        <div className="border-t border-slate-200 pt-2 mt-2">
            {/* Header */}
            <button
                onClick={onToggle}
                className="w-full flex items-center gap-2 px-3 py-2 hover:bg-slate-50 rounded-lg transition-colors group"
            >
                <span
                    className="material-symbols-outlined text-base text-slate-500 group-hover:text-slate-700 transition-transform"
                    style={{
                        transform: otherDocuments.isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                        transformOrigin: 'center',
                    }}
                >
                    chevron_right
                </span>
                <span className="material-symbols-outlined text-base text-[#9d4300]">description</span>
                <span className="font-semibold text-slate-700 text-sm">{otherDocuments.label}</span>
                <span className="ml-auto text-xs font-bold text-slate-400 bg-slate-100 px-2 py-1 rounded">
                    {totalOtherDocs}
                </span>
            </button>

            {/* Expanded Content */}
            {otherDocuments.isExpanded && (
                <div className="space-y-1 mt-1">
                    {/* Department Documents */}
                    {otherDocuments.departmentDocs.length > 0 && (
                        <DocumentCategory
                            title="Tài liệu Phòng ban"
                            icon="apartment"
                            iconBg="bg-blue-100"
                            documents={otherDocuments.departmentDocs}
                            selectedDocId={selectedDocId}
                            onSelectDocument={onSelectDocument}
                            searchQuery={searchQuery}
                        />
                    )}

                    {/* Personal Documents */}
                    {otherDocuments.personalDocs.length > 0 && (
                        <DocumentCategory
                            title="Tài liệu Cá nhân"
                            icon="person"
                            iconBg="bg-amber-100"
                            documents={otherDocuments.personalDocs}
                            selectedDocId={selectedDocId}
                            onSelectDocument={onSelectDocument}
                            searchQuery={searchQuery}
                        />
                    )}

                    {/* Company Documents */}
                    {otherDocuments.companyDocs.length > 0 && (
                        <DocumentCategory
                            title="Tài liệu Công ty"
                            icon="domain"
                            iconBg="bg-green-100"
                            documents={otherDocuments.companyDocs}
                            selectedDocId={selectedDocId}
                            onSelectDocument={onSelectDocument}
                            searchQuery={searchQuery}
                        />
                    )}
                </div>
            )}
        </div>
    )
}
