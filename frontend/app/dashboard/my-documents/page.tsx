'use client'

import { AppIcon } from '@/components/ui/AppIcon'
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { CreateFolderModal } from '@/components/features/documents/CreateFolderModal'
import { DocumentSidebar } from '@/components/features/documents/DocumentSidebar'
import { DocumentRow } from '@/components/features/documents/DocumentRow'
import { UploadDocumentModal } from '@/components/features/documents/UploadDocumentModal'
import { AccessDeniedPage } from '@/components/common/AccessDeniedPage'
import { useDepartmentOptions } from '@/hooks/useDepartmentOptions'
import { useRBAC } from '@/hooks/useRBAC'
import { useRouter } from 'next/navigation'
import {
    fetchPersonalFoldersWithDocuments,
    fetchSharedWithMeFoldersAndDocuments,
    FolderDocumentResponse,
    FolderWithDocuments,
    PersonalDocumentsOrganized,
    SharedDocumentsOrganized,
} from '@/services/folder'

function MyDocumentsPageContent() {
    const [organizedData, setOrganizedData] = useState<PersonalDocumentsOrganized>({ folders: [], unfoldered_documents: [] })
    const [sharedData, setSharedData] = useState<SharedDocumentsOrganized>({ folders: [], unfoldered_documents: [] })
    const [selectedDocument, setSelectedDocument] = useState<FolderDocumentResponse | null>(null)
    const [selectedFolder, setSelectedFolder] = useState<FolderWithDocuments | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [isSharedLoading, setIsSharedLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [sharedError, setSharedError] = useState<string | null>(null)
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
    const [isCreateFolderModalOpen, setIsCreateFolderModalOpen] = useState(false)
    const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())
    const [expandedSharedFolders, setExpandedSharedFolders] = useState<Set<string>>(new Set())

    const { hasPermission } = useRBAC()
    const canReadDepartments = hasPermission('department_read')
    const { data: departments } = useDepartmentOptions(canReadDepartments)
    const canUploadPersonalDocument = hasPermission('document_create')
    const canCreatePersonalFolder = hasPermission('folder_create')

    const loadPersonalDocuments = useCallback(async () => {
        setIsLoading(true)
        setError(null)

        try {
            const data = await fetchPersonalFoldersWithDocuments('personal')
            setOrganizedData(data)

            const expandedIds = new Set<string>()
            data.folders.forEach(folder => {
                if (folder.documents.length > 0) {
                    expandedIds.add(folder.id)
                }
            })
            if (data.unfoldered_documents.length > 0) {
                expandedIds.add('_unfoldered')
            }
            setExpandedFolders(expandedIds)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Không thể tải tài liệu cá nhân'
            setError(message)
            console.error('❌ Error loading personal documents:', err)
        } finally {
            setIsLoading(false)
        }
    }, [])

    const loadSharedDocuments = useCallback(async () => {
        setIsSharedLoading(true)
        setSharedError(null)

        try {
            const data = await fetchSharedWithMeFoldersAndDocuments()
            setSharedData(data)

            const expandedIds = new Set<string>()
            data.folders.forEach(folder => {
                if (folder.documents.length > 0) {
                    expandedIds.add(folder.id)
                }
            })
            if (data.unfoldered_documents.length > 0) {
                expandedIds.add('_shared_unfoldered')
            }
            setExpandedSharedFolders(expandedIds)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Không thể tải dữ liệu được chia sẻ'
            setSharedError(message)
            console.error('❌ Error loading shared documents:', err)
        } finally {
            setIsSharedLoading(false)
        }
    }, [])

    useEffect(() => {
        void loadPersonalDocuments()
        void loadSharedDocuments()
    }, [loadPersonalDocuments, loadSharedDocuments])

    const departmentMap = useMemo(() => {
        const map: Record<string, string> = {}
        if (!departments) return map

        const recurse = (items: any[]) => {
            items.forEach((department) => {
                if (!department || !department.id) return
                map[department.id] = department.name
                if (Array.isArray(department.sub_departments) && department.sub_departments.length > 0) {
                    recurse(department.sub_departments)
                }
            })
        }

        recurse(departments as any[])
        return map
    }, [departments])

    const totalDocuments = useMemo(() => {
        return organizedData.folders.reduce((sum, folder) => sum + folder.documents.length, 0) + organizedData.unfoldered_documents.length
    }, [organizedData])

    const totalSharedDocuments = useMemo(() => {
        return sharedData.folders.reduce((sum, folder) => sum + folder.documents.length, 0) + sharedData.unfoldered_documents.length
    }, [sharedData])

    const clearSelection = () => {
        setSelectedDocument(null)
        setSelectedFolder(null)
    }

    const toggleFolder = (folderId: string) => {
        const newExpanded = new Set(expandedFolders)
        if (newExpanded.has(folderId)) {
            newExpanded.delete(folderId)
        } else {
            newExpanded.add(folderId)
        }
        setExpandedFolders(newExpanded)
    }

    const toggleSharedFolder = (folderId: string) => {
        const newExpanded = new Set(expandedSharedFolders)
        if (newExpanded.has(folderId)) {
            newExpanded.delete(folderId)
        } else {
            newExpanded.add(folderId)
        }
        setExpandedSharedFolders(newExpanded)
    }

    const handleSelectDocument = (document: FolderDocumentResponse, folder: FolderWithDocuments | null) => {
        setSelectedDocument(document)
        setSelectedFolder(folder)
    }

    if (isLoading) {
        return (
            <div className="min-h-screen bg-[#f8f9ff] flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-10 h-10 border-4 border-[#9d4300]/20 border-t-[#9d4300] rounded-full animate-spin" />
                    <p className="text-sm text-slate-500 font-medium">Đang tải tài liệu của bạn...</p>
                </div>
            </div>
        )
    }

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
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-[#f8f9ff]">
            <main className="p-6 max-w-7xl mx-auto">
                <div className="mb-6 space-y-3">
                    <div className="rounded-[1.75rem] bg-white p-6 shadow-sm ring-1 ring-slate-100">
                        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                            <div>
                                <h1 className="text-2xl font-bold text-slate-900">Tài liệu của tôi</h1>
                                <p className="text-sm text-slate-500">Xem tài liệu cá nhân và tài liệu được chia sẻ theo phân quyền ACL.</p>
                            </div>
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
                                <div className="rounded-3xl bg-[#f4f9ff] px-4 py-3 text-sm text-slate-600">
                                    {totalDocuments} tài liệu cá nhân • {totalSharedDocuments} tài liệu được chia sẻ
                                </div>
                                {(canUploadPersonalDocument || canCreatePersonalFolder) && (
                                <div className="flex flex-col gap-2 sm:flex-row">
                                    {canUploadPersonalDocument && (
                                    <button
                                        onClick={() => setIsUploadModalOpen(true)}
                                        className="inline-flex items-center justify-center gap-2 rounded-3xl bg-[#9d4300] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#b75b00]"
                                    >
                                        <AppIcon name="upload_file" className="text-base" />
                                        Tải lên cá nhân
                                    </button>
                                    )}
                                    {canCreatePersonalFolder && (
                                    <button
                                        onClick={() => setIsCreateFolderModalOpen(true)}
                                        className="inline-flex items-center justify-center gap-2 rounded-3xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                                    >
                                        <AppIcon name="create_new_folder" className="text-base" />
                                        Tạo thư mục cá nhân
                                    </button>
                                    )}
                                </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-12 gap-6">
                    <div className="col-span-12 lg:col-span-7 space-y-6">
                        <div className="bg-white shadow-sm ring-1 ring-slate-100 rounded-3xl overflow-hidden">
                            <div className="border-b border-slate-100 px-5 py-4">
                                <h2 className="text-sm font-semibold text-slate-900">Thư mục & Tài liệu cá nhân</h2>
                                <p className="text-xs text-slate-500 mt-1">Hiển thị các thư mục và tài liệu với access_scope = "Cá nhân".</p>
                            </div>
                            <div className="p-4 space-y-2 max-h-[420px] overflow-y-auto">
                                {organizedData.folders.length === 0 && organizedData.unfoldered_documents.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center py-20 text-center gap-3 text-slate-500">
                                        <AppIcon name="folder_open" className="text-5xl" />
                                        <p className="text-sm font-semibold">Chưa có tài liệu cá nhân</p>
                                        <p className="text-xs max-w-xs">Bạn có thể tải lên tài liệu mới với access_scope "personal" từ trang Kho tài liệu.</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {organizedData.folders.map((folder) => (
                                            <div key={folder.id} className="border border-slate-200 rounded-lg overflow-hidden">
                                                <button
                                                    onClick={() => toggleFolder(folder.id)}
                                                    className="w-full flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100 transition"
                                                >
                                                    <div className="flex items-center gap-2">
                                                        <AppIcon name={expandedFolders.has(folder.id) ? 'folder_open' : 'folder'} className="text-lg text-[#9d4300]" />
                                                        <div className="text-left">
                                                            <p className="text-sm font-semibold text-slate-900">{folder.name}</p>
                                                            <p className="text-xs text-slate-500">{folder.documents.length} tài liệu</p>
                                                        </div>
                                                    </div>
                                                    <AppIcon name={expandedFolders.has(folder.id) ? 'expand_less' : 'expand_more'} className="text-lg text-slate-400" />
                                                </button>

                                                {expandedFolders.has(folder.id) && (
                                                    <div className="border-t border-slate-200 p-2 bg-white">
                                                        {folder.documents.length === 0 ? (
                                                            <div className="text-center py-4 text-slate-400">
                                                                <p className="text-xs">Thư mục rỗng</p>
                                                            </div>
                                                        ) : (
                                                            <div className="space-y-1">
                                                                {folder.documents.map((doc) => (
                                                                    <DocumentRow
                                                                        key={doc.id}
                                                                        document={doc}
                                                                        isSelected={selectedDocument?.id === doc.id}
                                                                        onSelect={() => handleSelectDocument(doc, folder)}
                                                                        folderName={folder.name}
                                                                        departmentName={departmentMap[doc.department || doc.department_id || '']}
                                                                    />
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        ))}

                                        {organizedData.unfoldered_documents.length > 0 && (
                                            <div className="border border-slate-200 rounded-lg overflow-hidden">
                                                <button
                                                    onClick={() => toggleFolder('_unfoldered')}
                                                    className="w-full flex items-center justify-between p-3 bg-amber-50 hover:bg-amber-100 transition"
                                                >
                                                    <div className="flex items-center gap-2">
                                                        <AppIcon name="inbox" className="text-lg text-amber-600" />
                                                        <div className="text-left">
                                                            <p className="text-sm font-semibold text-slate-900">Tài liệu chưa phân loại</p>
                                                            <p className="text-xs text-slate-500">{organizedData.unfoldered_documents.length} tài liệu</p>
                                                        </div>
                                                    </div>
                                                    <AppIcon name={expandedFolders.has('_unfoldered') ? 'expand_less' : 'expand_more'} className="text-lg text-slate-400" />
                                                </button>

                                                {expandedFolders.has('_unfoldered') && (
                                                    <div className="border-t border-slate-200 p-2 bg-white space-y-1">
                                                        {organizedData.unfoldered_documents.map((doc) => (
                                                            <DocumentRow
                                                                key={doc.id}
                                                                document={doc}
                                                                isSelected={selectedDocument?.id === doc.id}
                                                                onSelect={() => handleSelectDocument(doc, null)}
                                                                departmentName={departmentMap[doc.department || doc.department_id || '']}
                                                            />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="bg-white shadow-sm ring-1 ring-slate-100 rounded-3xl overflow-hidden">
                            <div className="border-b border-slate-100 px-5 py-4">
                                <h2 className="text-sm font-semibold text-slate-900">Được chia sẻ với tôi</h2>
                                <p className="text-xs text-slate-500 mt-1">FolderPermission và DocumentPermission sẽ ghi đè access_scope để hiển thị dữ liệu chia sẻ.</p>
                            </div>
                            <div className="px-5 py-3 border-b border-slate-100 bg-slate-50/60">
                                <p className="text-xs text-slate-600">
                                    {totalSharedDocuments} tài liệu được chia sẻ • {sharedData.folders.length} thư mục được chia sẻ
                                </p>
                            </div>
                            <div className="p-4 space-y-2 max-h-[420px] overflow-y-auto">
                                {isSharedLoading ? (
                                    <div className="flex items-center justify-center py-12">
                                        <div className="flex items-center gap-2 text-slate-500 text-sm">
                                            <div className="w-5 h-5 border-2 border-[#9d4300]/20 border-t-[#9d4300] rounded-full animate-spin" />
                                            Đang tải dữ liệu chia sẻ...
                                        </div>
                                    </div>
                                ) : sharedError ? (
                                    <div className="text-center py-12 text-red-500 text-sm">{sharedError}</div>
                                ) : sharedData.folders.length === 0 && sharedData.unfoldered_documents.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center py-14 text-center gap-3 text-slate-500">
                                        <AppIcon name="folder_shared" className="text-4xl" />
                                        <p className="text-sm font-semibold">Chưa có dữ liệu được chia sẻ</p>
                                        <p className="text-xs max-w-xs">Khi có ai đó share folder hoặc tài liệu cho bạn, dữ liệu sẽ hiển thị ở đây.</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {sharedData.folders.map((folder) => (
                                            <div key={folder.id} className="border border-slate-200 rounded-lg overflow-hidden">
                                                <button
                                                    onClick={() => toggleSharedFolder(folder.id)}
                                                    className="w-full flex items-center justify-between p-3 bg-blue-50 hover:bg-blue-100 transition"
                                                >
                                                    <div className="flex items-center gap-2">
                                                        <AppIcon name={expandedSharedFolders.has(folder.id) ? 'folder_open' : 'folder_shared'} className="text-lg text-blue-700" />
                                                        <div className="text-left">
                                                            <p className="text-sm font-semibold text-slate-900">{folder.name}</p>
                                                            <p className="text-xs text-slate-500">{folder.documents.length} tài liệu được chia sẻ</p>
                                                        </div>
                                                    </div>
                                                    <AppIcon name={expandedSharedFolders.has(folder.id) ? 'expand_less' : 'expand_more'} className="text-lg text-slate-400" />
                                                </button>

                                                {expandedSharedFolders.has(folder.id) && (
                                                    <div className="border-t border-slate-200 p-2 bg-white">
                                                        {folder.documents.length === 0 ? (
                                                            <div className="text-center py-4 text-slate-400">
                                                                <p className="text-xs">Thư mục này đang chưa có tài liệu khả dụng</p>
                                                            </div>
                                                        ) : (
                                                            <div className="space-y-1">
                                                                {folder.documents.map((doc) => (
                                                                    <DocumentRow
                                                                        key={doc.id}
                                                                        document={doc}
                                                                        isSelected={selectedDocument?.id === doc.id}
                                                                        onSelect={() => handleSelectDocument(doc, folder)}
                                                                        folderName={folder.name}
                                                                        departmentName={departmentMap[doc.department || doc.department_id || '']}
                                                                    />
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        ))}

                                        {sharedData.unfoldered_documents.length > 0 && (
                                            <div className="border border-slate-200 rounded-lg overflow-hidden">
                                                <button
                                                    onClick={() => toggleSharedFolder('_shared_unfoldered')}
                                                    className="w-full flex items-center justify-between p-3 bg-cyan-50 hover:bg-cyan-100 transition"
                                                >
                                                    <div className="flex items-center gap-2">
                                                        <AppIcon name="share" className="text-lg text-cyan-700" />
                                                        <div className="text-left">
                                                            <p className="text-sm font-semibold text-slate-900">Tài liệu chia sẻ trực tiếp</p>
                                                            <p className="text-xs text-slate-500">{sharedData.unfoldered_documents.length} tài liệu</p>
                                                        </div>
                                                    </div>
                                                    <AppIcon name={expandedSharedFolders.has('_shared_unfoldered') ? 'expand_less' : 'expand_more'} className="text-lg text-slate-400" />
                                                </button>

                                                {expandedSharedFolders.has('_shared_unfoldered') && (
                                                    <div className="border-t border-slate-200 p-2 bg-white space-y-1">
                                                        {sharedData.unfoldered_documents.map((doc) => (
                                                            <DocumentRow
                                                                key={doc.id}
                                                                document={doc}
                                                                isSelected={selectedDocument?.id === doc.id}
                                                                onSelect={() => handleSelectDocument(doc, null)}
                                                                departmentName={departmentMap[doc.department || doc.department_id || '']}
                                                            />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    <DocumentSidebar
                        document={selectedDocument}
                        folder={selectedFolder}
                        onClose={clearSelection}
                        onDocumentDeleted={async () => {
                            await Promise.all([
                                loadPersonalDocuments(),
                                loadSharedDocuments(),
                            ])
                        }}
                    />
                </div>
                {canUploadPersonalDocument && (
                <UploadDocumentModal
                    isOpen={isUploadModalOpen}
                    onClose={() => setIsUploadModalOpen(false)}
                    onSuccess={() => {
                        void loadPersonalDocuments()
                        void loadSharedDocuments()
                    }}
                    defaultAccessScope="personal"
                    allowedScopes={['personal']}
                />
                )}
                {canCreatePersonalFolder && (
                <CreateFolderModal
                    isOpen={isCreateFolderModalOpen}
                    onClose={() => setIsCreateFolderModalOpen(false)}
                    onSuccess={() => {
                        void loadPersonalDocuments()
                        void loadSharedDocuments()
                    }}
                    defaultAccessScope="personal"
                    allowedScopes={['personal']}
                />
                )}
            </main>
        </div>
    )
}

export default function MyDocumentsPage() {
    const router = useRouter()
    const { hasPermission } = useRBAC()
    const canReadDocuments = hasPermission('document_read')
    const canReadFolders = hasPermission('folder_read')

    if (!canReadDocuments || !canReadFolders) {
        return (
            <AccessDeniedPage
                title="Truy cập bị hạn chế"
                message="Bạn cần quyền document_read để truy cập Tài liệu của tôi."
                icon="🔒"
                showBackButton={true}
                onGoBack={() => router.push('/dashboard')}
            />
        )
    }

    return <MyDocumentsPageContent />
}
