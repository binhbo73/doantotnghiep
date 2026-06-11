'use client'

import { AppIcon } from '@/components/ui/AppIcon'
/**
 * Documents Page
 * RBAC:
 * - document_read/folder_read: browse documents
 * - document_share/document_update/folder_update/folder_delete: permissions tab
 * - document_create: upload documents
 * - folder_create: create folders
 */

import React, { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import {
    DocumentHeader,
    FolderTree,
    DocumentSidebar,
    UploadDocumentModal,
    CreateFolderModal,
} from '@/components/features/documents'
import { DocumentsPermissionsWorkspace } from '@/components/features/documents/DocumentsPermissionsWorkspace'
import { useDocumentStore } from '@/hooks/useDocumentStore'
import { useRBAC } from '@/hooks/useRBAC'
import { AccessDeniedPage } from '@/components/common/AccessDeniedPage'
import { useRouter } from 'next/navigation'
import {
    fetchSharedWithMeFoldersAndDocuments,
    FolderResponse,
    FolderWithDocuments,
    SharedDocumentsOrganized,
} from '@/services/folder'
import { FolderTreeNode, OtherDocumentsNode } from '@/hooks/useDocumentStore'
import { deleteFolder } from '@/services/document'
import { DeleteConfirmDialog } from '@/components/common/DeleteConfirmDialog'
import { getSafeDeleteBlockers } from '@/lib/safeDelete'

type DocumentsPageTab = 'browse' | 'permissions'

function PageTabButton({
    active,
    label,
    icon,
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
                    <AppIcon name={icon} className={`text-base ${active ? 'text-white' : disabled ? 'text-slate-300' : 'text-[#9d4300]'}`} />
                </div>
                <div className="min-w-0">
                    <p className="text-[13px] font-bold">{label}</p>
                    {disabled && (
                        <p className="text-[10px] opacity-60">Yêu cầu quyền phân quyền tài liệu</p>
                    )}
                </div>
            </div>
        </button>
    )
}

function collectSharedFolderIds(folders: FolderWithDocuments[]): Set<string> {
    const folderIds = new Set<string>()

    const walk = (items: FolderWithDocuments[]) => {
        items.forEach((folder) => {
            folderIds.add(folder.id)
            if (Array.isArray(folder.sub_folders) && folder.sub_folders.length > 0) {
                walk(folder.sub_folders as FolderWithDocuments[])
            }
        })
    }

    walk(folders)
    return folderIds
}

function collectSharedDocumentIds(sharedData: SharedDocumentsOrganized): Set<string> {
    const documentIds = new Set<string>()

    const walk = (items: FolderWithDocuments[]) => {
        items.forEach((folder) => {
            folder.documents.forEach((document) => documentIds.add(document.id))
            if (Array.isArray(folder.sub_folders) && folder.sub_folders.length > 0) {
                walk(folder.sub_folders as FolderWithDocuments[])
            }
        })
    }

    walk(sharedData.folders)
    sharedData.unfoldered_documents.forEach((document) => documentIds.add(document.id))

    return documentIds
}

function filterBrowseTree(
    nodes: FolderTreeNode[],
    excludedFolderIds: Set<string>,
    excludedDocumentIds: Set<string>
): FolderTreeNode[] {
    return nodes
        .filter((node) => !excludedFolderIds.has(node.folder.id))
        .map((node) => ({
            ...node,
            children: filterBrowseTree(node.children, excludedFolderIds, excludedDocumentIds),
            documents: node.documents.filter((document) => !excludedDocumentIds.has(document.id)),
        }))
}

function filterOtherDocuments(
    otherDocuments: OtherDocumentsNode,
    excludedDocumentIds: Set<string>
): OtherDocumentsNode {
    return {
        ...otherDocuments,
        departmentDocs: otherDocuments.departmentDocs.filter((document) => !excludedDocumentIds.has(document.id)),
        personalDocs: otherDocuments.personalDocs.filter((document) => !excludedDocumentIds.has(document.id)),
        companyDocs: otherDocuments.companyDocs.filter((document) => !excludedDocumentIds.has(document.id)),
    }
}

function DocumentsPageContent() {
    const [activeTab, setActiveTab] = useState<DocumentsPageTab>('browse')
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
    const [isCreateFolderModalOpen, setIsCreateFolderModalOpen] = useState(false)
    const [uploadTargetFolder, setUploadTargetFolder] = useState<FolderResponse | null>(null)
    const [createParentFolder, setCreateParentFolder] = useState<FolderResponse | null>(null)
    const [folderToDelete, setFolderToDelete] = useState<FolderResponse | null>(null)
    const [isDeletingFolder, setIsDeletingFolder] = useState(false)
    const [folderDeleteBlockers, setFolderDeleteBlockers] = useState<string[]>([])
    const [sharedWithMe, setSharedWithMe] = useState<SharedDocumentsOrganized>({ folders: [], unfoldered_documents: [] })
    const { hasPermission, hasAnyPermission } = useRBAC()
    const canReadDocuments = hasPermission('document_read')
    const canReadFolders = hasPermission('folder_read')

    const {
        tree,
        otherDocuments,
        allDocuments,
        selectedDocument,
        selectedFolder,
        isLoading,
        error,
        searchQuery,
        setSearchQuery,
        toggleFolder,
        toggleOtherDocuments,
        refreshFolderDocuments,
        refreshOtherDocuments,
        selectDocument,
        clearSelection,
        removeFolder,
        refetch,
        getStats,
    } = useDocumentStore({
        enabled: canReadDocuments || canReadFolders,
        canReadDocuments,
        canReadFolders,
    })

    const stats = getStats()

    const shouldHideSharedItems = false

    useEffect(() => {
        if (!canReadDocuments) {
            setSharedWithMe({ folders: [], unfoldered_documents: [] })
            return
        }

        let isMounted = true

        void fetchSharedWithMeFoldersAndDocuments()
            .then((data) => {
                if (isMounted) {
                    setSharedWithMe(data)
                }
            })
            .catch((err) => {
                console.warn('Failed to load shared documents for filtering:', err)
                if (isMounted) {
                    setSharedWithMe({ folders: [], unfoldered_documents: [] })
                }
            })

        return () => {
            isMounted = false
        }
    }, [canReadDocuments])

    const browseTree = useMemo(() => {
        if (!shouldHideSharedItems) {
            return tree
        }

        const excludedFolderIds = collectSharedFolderIds(sharedWithMe.folders)
        const excludedDocumentIds = collectSharedDocumentIds(sharedWithMe)
        return filterBrowseTree(tree, excludedFolderIds, excludedDocumentIds)
    }, [sharedWithMe, shouldHideSharedItems, tree])

    const browseOtherDocuments = useMemo(() => {
        if (!shouldHideSharedItems) {
            return otherDocuments
        }

        const excludedDocumentIds = collectSharedDocumentIds(sharedWithMe)
        return filterOtherDocuments(otherDocuments, excludedDocumentIds)
    }, [otherDocuments, sharedWithMe, shouldHideSharedItems])

    // Permissions for document page features
    const canManagePermissions = hasAnyPermission(['document_share', 'document_update', 'folder_update', 'folder_delete'])
    const canCreateFolder = hasPermission('folder_create')
    const canDeleteFolder = hasPermission('folder_delete')
    const canUpload = hasPermission('document_create')

    const openUploadModal = (folder?: FolderResponse | null) => {
        setUploadTargetFolder(folder ?? null)
        setIsUploadModalOpen(true)
    }

    const closeUploadModal = () => {
        setIsUploadModalOpen(false)
        setUploadTargetFolder(null)
    }

    const openCreateFolderModal = (parentFolder?: FolderResponse | null) => {
        setCreateParentFolder(parentFolder ?? null)
        setIsCreateFolderModalOpen(true)
    }

    const closeCreateFolderModal = () => {
        setIsCreateFolderModalOpen(false)
        setCreateParentFolder(null)
    }

    const openFolderDeleteDialog = (folder: FolderResponse) => {
        setFolderDeleteBlockers([])
        setFolderToDelete(folder)
    }

    const handleDeleteFolder = async () => {
        if (!folderToDelete || !canDeleteFolder) return

        const deletedFolder = folderToDelete
        setIsDeletingFolder(true)
        try {
            await deleteFolder(deletedFolder.id)
            clearSelection()
            removeFolder(deletedFolder.id)
            setFolderToDelete(null)
            setFolderDeleteBlockers([])
            toast.success(`Đã xóa thư mục "${deletedFolder.name}"`)
        } catch (err) {
            const blockers = getSafeDeleteBlockers(err)
            if (blockers) {
                const items = [
                    blockers.child_folders
                        ? `${blockers.child_folders} thư mục con`
                        : null,
                    blockers.documents
                        ? `${blockers.documents} tài liệu`
                        : null,
                ].filter((item): item is string => Boolean(item))

                setFolderDeleteBlockers(
                    items.length > 0
                        ? items
                        : ['Thư mục vẫn còn dữ liệu liên quan']
                )
                return
            }

            const message = err instanceof Error
                ? err.message
                : 'Không thể xóa thư mục'
            toast.error(message)
        } finally {
            setIsDeletingFolder(false)
        }
    }

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
                        <AppIcon name="error" className="text-3xl text-red-400" />
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
                    onCreateFolder={canCreateFolder ? () => openCreateFolderModal() : undefined}
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
                            tree={browseTree}
                            otherDocuments={browseOtherDocuments}
                            selectedDocId={selectedDocument?.id || null}
                            onToggleFolder={toggleFolder}
                            onToggleOtherDocuments={toggleOtherDocuments}
                            onSelectDocument={selectDocument}
                            onUploadToFolder={canUpload ? openUploadModal : undefined}
                            onCreateSubfolder={canCreateFolder ? openCreateFolderModal : undefined}
                            onDeleteFolder={canDeleteFolder ? openFolderDeleteDialog : undefined}
                            deletingFolderId={isDeletingFolder ? folderToDelete?.id : null}
                            searchQuery={searchQuery}
                            showPersonal={false}
                        />

                        {/* Document Detail Sidebar */}
                        <DocumentSidebar
                            document={selectedDocument}
                            folder={selectedFolder}
                            onClose={clearSelection}
                            onSelectVersion={(versionDocument) => {
                                selectDocument(versionDocument, selectedFolder || undefined)
                            }}
                            onVersionCreated={() => {
                                void refetch()
                            }}
                        />
                    </div>
                ) : (
                    <DocumentsPermissionsWorkspace
                        tree={tree}
                        otherDocuments={otherDocuments}
                        allDocuments={allDocuments}
                        sharedWithMe={sharedWithMe}
                        selectedDocument={selectedDocument}
                        selectedFolder={selectedFolder}
                        onSelectDocument={selectDocument}
                    />
                )}
            </main>

            {/* Floating Upload Button */}
            {canUpload && (
                <button
                    onClick={() => openUploadModal()}
                    className="fixed bottom-10 right-10 w-16 h-16 bg-[#9d4300] text-white rounded-full shadow-2xl flex items-center justify-center hover:scale-110 active:scale-95 transition-all group z-50 hover:shadow-[#f97316]/50"
                >
                    <AppIcon name="upload_file" className="text-3xl" />
                    <span className="absolute right-full mr-4 bg-[#0d1c2e] text-white px-3 py-1 rounded-lg text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap shadow-lg">
                        Tải lên Tài liệu
                    </span>
                </button>
            )}

            {/* Upload Modal */}
            <UploadDocumentModal
                isOpen={isUploadModalOpen}
                onClose={closeUploadModal}
                onSuccess={(folderId) => {
                    if (folderId) {
                        void refreshFolderDocuments(folderId, uploadTargetFolder?.id === folderId)
                    } else {
                        void refreshOtherDocuments()
                    }
                }}
                defaultAccessScope={uploadTargetFolder?.access_scope}
                defaultDepartmentId={uploadTargetFolder?.department_id}
                defaultFolderId={uploadTargetFolder?.id}
            />

            {/* Create Folder Modal */}
            {canCreateFolder && (
                <CreateFolderModal
                    isOpen={isCreateFolderModalOpen}
                    onClose={closeCreateFolderModal}
                    onSuccess={() => {
                        void refetch()
                    }}
                    defaultAccessScope={createParentFolder?.access_scope}
                    defaultDepartmentId={createParentFolder?.department_id}
                    defaultParentFolderId={createParentFolder?.id}
                />
            )}

            <DeleteConfirmDialog
                open={folderToDelete !== null}
                title={folderDeleteBlockers.length > 0 ? 'Không thể xóa thư mục' : 'Xóa thư mục?'}
                description={folderDeleteBlockers.length > 0
                    ? 'Đây là cơ chế bảo vệ dữ liệu. Thư mục chỉ được xóa sau khi đã xử lý hết nội dung bên trong.'
                    : 'Chỉ có thể xóa thư mục rỗng. Hệ thống sẽ từ chối nếu thư mục còn tài liệu hoặc thư mục con.'}
                resourceName={folderToDelete?.name}
                isDeleting={isDeletingFolder}
                blockedItems={folderDeleteBlockers}
                onOpenChange={(open) => {
                    if (!open) {
                        setFolderToDelete(null)
                        setFolderDeleteBlockers([])
                    }
                }}
                onConfirm={handleDeleteFolder}
            />
        </div>
    )
}

export default function DocumentsPage() {
    const router = useRouter()
    const { hasAnyPermission } = useRBAC()
    const canBrowseDocuments = hasAnyPermission(['document_read', 'folder_read'])

    if (!canBrowseDocuments) {
        return (
            <AccessDeniedPage
                title="Truy cập bị hạn chế"
                message="Bạn cần quyền document_read hoặc folder_read để truy cập Kho tài liệu."
                icon="🔒"
                showBackButton={true}
                onGoBack={() => router.push('/dashboard')}
            />
        )
    }

    return <DocumentsPageContent />
}
