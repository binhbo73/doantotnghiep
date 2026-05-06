'use client'

/**
 * Documents Page
 * RBAC:
 * - All authenticated users can browse documents (tab "Duyệt tài liệu")
 * - Only Admin can access the "Phân quyền" tab
 * - Upload button visibility: Admin + Manager can upload, User can only upload personal
 * - Create Folder: Admin + Manager + Users in their own department
 */

import React, { useState } from 'react'
import {
    DocumentHeader,
    FolderTree,
    OtherDocuments,
    DocumentSidebar,
    UploadDocumentModal,
    CreateFolderModal,
} from '@/components/features/documents'
import { DocumentsPermissionsWorkspace } from '@/components/features/documents/DocumentsPermissionsWorkspace'
import { useDocumentStore } from '@/hooks/useDocumentStore'
import { useRBAC } from '@/hooks/useRBAC'
import { useAuthContext } from '@/context'

type DocumentsPageTab = 'browse' | 'permissions'

function PageTabButton({
    active,
    label,
    icon,
    description,
    onClick,
    disabled,
}: {
    active: boolean
    label: string
    icon: string
    description: string
    onClick: () => void
    disabled?: boolean
}) {
    return (
        <button
            onClick={onClick}
            disabled={disabled}
            className={`flex-1 rounded-2xl px-3.5 py-2.5 text-left transition-all ${active
                ? 'bg-[#9d4300] text-white shadow-lg shadow-[#9d4300]/20'
                : disabled
                    ? 'border border-slate-100 bg-slate-50 text-slate-300 cursor-not-allowed'
                    : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                }`}
        >
            <div className="flex items-center gap-2.5">
                <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${active ? 'bg-white/15' : disabled ? 'bg-slate-100' : 'bg-[#fff3e0]'}`}>
                    <span className={`material-symbols-outlined text-base ${active ? 'text-white' : disabled ? 'text-slate-300' : 'text-[#9d4300]'}`}>{icon}</span>
                </div>
                <div className="min-w-0">
                    <p className="text-[13px] font-bold">{label}</p>
                    {disabled && (
                        <p className="text-[10px] opacity-60">Yêu cầu quyền Admin</p>
                    )}
                </div>
            </div>
        </button>
    )
}

export default function DocumentsPage() {
    const [activeTab, setActiveTab] = useState<DocumentsPageTab>('browse')
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
    const [isCreateFolderModalOpen, setIsCreateFolderModalOpen] = useState(false)
    const { isAdmin, isTruongPhong, hasGlobalPermission } = useRBAC()

    const { user } = useAuthContext()
    const {
        tree,
        otherDocuments,
        selectedDocument,
        selectedFolder,
        isLoading,
        error,
        searchQuery,
        setSearchQuery,
        toggleFolder,
        toggleOtherDocuments,
        selectDocument,
        clearSelection,
        refetch,
        getStats,
    } = useDocumentStore()

    const stats = getStats()

    // Permissions for document page features
    const canManagePermissions = isAdmin()
    const canCreateFolder = isAdmin() || isTruongPhong() || !!user?.department_id
    const canUpload = isAdmin() || isTruongPhong() || hasGlobalPermission('create', 'document')

    // ── Loading State ──────────────────────────────────────
    if (isLoading) {
        return (
            <div className="min-h-screen bg-[#f8f9ff] flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-10 h-10 border-4 border-[#9d4300]/20 border-t-[#9d4300] rounded-full animate-spin" />
                    <p className="text-sm text-slate-500 font-medium">Đang tải kho tài liệu...</p>
                </div>
            </div>
        )
    }

    // ── Error State ────────────────────────────────────────
    if (error) {
        return (
            <div className="min-h-screen bg-[#f8f9ff] flex items-center justify-center">
                <div className="flex flex-col items-center gap-4 max-w-sm text-center">
                    <div className="w-16 h-16 rounded-2xl bg-red-50 flex items-center justify-center">
                        <span className="material-symbols-outlined text-3xl text-red-400">error</span>
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-slate-700 mb-1">Không thể tải dữ liệu</p>
                        <p className="text-xs text-slate-400">{error}</p>
                    </div>
                    <button
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 bg-[#9d4300] text-white rounded-xl text-xs font-bold hover:bg-[#b75b00] transition-colors"
                    >
                        Thử lại
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-[#f8f9ff]">
            <main className="p-6 max-w-7xl mx-auto">
                {/* Header */}
                <DocumentHeader
                    title="Kho Tài liệu Hệ thống"
                    subtitle="Quản lý và tìm kiếm tất cả tài liệu, quy trình kỹ thuật tập trung trong hệ thống tri thức doanh nghiệp."
                    totalFolders={stats.totalFolders}
                    totalDocuments={stats.totalDocuments}
                    searchQuery={searchQuery}
                    onSearchChange={setSearchQuery}
                    onCreateFolder={canCreateFolder ? () => setIsCreateFolderModalOpen(true) : undefined}
                    compact={activeTab === 'permissions'}
                />

                {/* Page Tabs */}
                <div className={`mb-4 rounded-[1.5rem] border border-slate-100 bg-white p-1.5 shadow-sm ${activeTab === 'permissions' ? 'mb-3' : 'md:mb-6'}`}>
                    <div className="grid grid-cols-1 gap-1.5 md:grid-cols-2">
                        <PageTabButton
                            active={activeTab === 'browse'}
                            label="Duyệt tài liệu"
                            icon="folder_open"
                            description="Xem cây thư mục và mở tài liệu trong kho"
                            onClick={() => setActiveTab('browse')}
                        />
                        <PageTabButton
                            active={activeTab === 'permissions'}
                            label="Phân quyền"
                            icon="admin_panel_settings"
                            description="Quản lý folder_permission và document_permission"
                            onClick={() => canManagePermissions && setActiveTab('permissions')}
                            disabled={!canManagePermissions}
                        />
                    </div>
                </div>

                {activeTab === 'browse' ? (
                    /* Main Content: Tree + Sidebar */
                    <div className="grid grid-cols-12 gap-6">
                        {/* Folder Tree */}
                        <FolderTree
                            tree={tree}
                            otherDocuments={otherDocuments}
                            selectedDocId={selectedDocument?.id || null}
                            onToggleFolder={toggleFolder}
                            onToggleOtherDocuments={toggleOtherDocuments}
                            onSelectDocument={selectDocument}
                            searchQuery={searchQuery}
                            showPersonal={false}
                        />

                        {/* Document Detail Sidebar */}
                        <DocumentSidebar
                            document={selectedDocument}
                            folder={selectedFolder}
                            onClose={clearSelection}
                        />
                    </div>
                ) : (
                    <DocumentsPermissionsWorkspace
                        tree={tree}
                        otherDocuments={otherDocuments}
                        selectedDocument={selectedDocument}
                        selectedFolder={selectedFolder}
                        onSelectDocument={selectDocument}
                    />
                )}
            </main>

            {/* Floating Upload Button */}
            {canUpload && (
                <button
                    onClick={() => setIsUploadModalOpen(true)}
                    className="fixed bottom-10 right-10 w-16 h-16 bg-[#9d4300] text-white rounded-full shadow-2xl flex items-center justify-center hover:scale-110 active:scale-95 transition-all group z-50 hover:shadow-[#f97316]/50"
                >
                    <span className="material-symbols-outlined text-3xl">upload_file</span>
                    <span className="absolute right-full mr-4 bg-[#0d1c2e] text-white px-3 py-1 rounded-lg text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap shadow-lg">
                        Tải lên Tài liệu
                    </span>
                </button>
            )}

            {/* Upload Modal */}
            <UploadDocumentModal
                isOpen={isUploadModalOpen}
                onClose={() => setIsUploadModalOpen(false)}
                onSuccess={() => {
                    void refetch()
                }}
            />

            {/* Create Folder Modal - Admin + Manager only */}
            {canCreateFolder && (
                <CreateFolderModal
                    isOpen={isCreateFolderModalOpen}
                    onClose={() => setIsCreateFolderModalOpen(false)}
                    onSuccess={() => {
                        void refetch()
                    }}
                />
            )}
        </div>
    )
}
