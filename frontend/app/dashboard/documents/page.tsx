'use client'

import React from 'react'
import {
    DocumentHeader,
    FolderTree,
    OtherDocuments,
    DocumentSidebar,
} from '@/components/features/documents'
import { useDocumentStore } from '@/hooks/useDocumentStore'

export default function DocumentsPage() {
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
        getStats,
    } = useDocumentStore()

    const stats = getStats()

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
                />

                {/* Main Content: Tree + Sidebar */}
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
                    />

                    {/* Document Detail Sidebar */}
                    <DocumentSidebar
                        document={selectedDocument}
                        folder={selectedFolder}
                        onClose={clearSelection}
                    />
                </div>
            </main>

            {/* Floating Upload Button */}
            <button
                className="fixed bottom-10 right-10 w-16 h-16 bg-[#9d4300] text-white rounded-full shadow-2xl flex items-center justify-center hover:scale-110 active:scale-95 transition-all group z-50 hover:shadow-[#f97316]/50"
            >
                <span className="material-symbols-outlined text-3xl">upload_file</span>
                <span className="absolute right-full mr-4 bg-[#0d1c2e] text-white px-3 py-1 rounded-lg text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap shadow-lg">
                    Tải lên Tài liệu
                </span>
            </button>
        </div>
    )
}
