'use client'

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { CreateFolderModal } from '@/components/features/documents/CreateFolderModal'
import { DocumentSidebar } from '@/components/features/documents/DocumentSidebar'
import { DocumentRow } from '@/components/features/documents/DocumentRow'
import { UploadDocumentModal } from '@/components/features/documents/UploadDocumentModal'
import { useDepartmentOptions } from '@/hooks/useDepartmentOptions'
import { useRBAC } from '@/hooks/useRBAC'
import { fetchPersonalFoldersWithDocuments, FolderDocumentResponse, FolderWithDocuments, PersonalDocumentsOrganized } from '@/services/folder'

export default function MyDocumentsPage() {
    const [organizedData, setOrganizedData] = useState<PersonalDocumentsOrganized>({ folders: [], unfoldered_documents: [] })
    const [selectedDocument, setSelectedDocument] = useState<FolderDocumentResponse | null>(null)
    const [selectedFolder, setSelectedFolder] = useState<FolderWithDocuments | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
    const [isCreateFolderModalOpen, setIsCreateFolderModalOpen] = useState(false)
    const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())

    const { data: departments } = useDepartmentOptions()
    const { isAdmin } = useRBAC()

    const loadPersonalDocuments = useCallback(async () => {
        setIsLoading(true)
        setError(null)

        try {
            const data = await fetchPersonalFoldersWithDocuments('personal')
            setOrganizedData(data)

            // Auto-expand folders that have documents
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

    useEffect(() => {
        void loadPersonalDocuments()
    }, [loadPersonalDocuments])

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
        return organizedData.folders.reduce((sum, folder) => sum + folder.documents.length, 0) +
            organizedData.unfoldered_documents.length
    }, [organizedData])

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
                        <span className="material-symbols-outlined text-3xl text-red-400">error</span>
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-slate-700 mb-1">Không thể tải dữ liệu</p>
                        <p className="text-xs text-slate-400">{error}</p>
                    </div>
                </div>
            </div>
        )
    }

    if (isAdmin()) {
        return (
            <div className="min-h-screen bg-[#f8f9ff] flex items-center justify-center px-4">
                <div className="max-w-xl bg-white rounded-3xl shadow-sm ring-1 ring-slate-200 p-8 text-center">
                    <span className="material-symbols-outlined text-5xl text-[#9d4300] mb-4">lock</span>
                    <h1 className="text-xl font-bold text-slate-900 mb-2">Trang này chỉ dành cho Nhân viên và Trưởng phòng</h1>
                    <p className="text-sm text-slate-500">Quản trị viên không cần truy cập tab "Tài liệu của tôi". Vui lòng chọn một mục khác trong sidebar.</p>
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
                                <p className="text-sm text-slate-500">Xem các tài liệu cá nhân được organized theo thư mục và access_scope = personal.</p>
                            </div>
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
                                <div className="rounded-3xl bg-[#f4f9ff] px-4 py-3 text-sm text-slate-600">
                                    {totalDocuments} tài liệu • {organizedData.folders.length} thư mục
                                </div>
                                <div className="flex flex-col gap-2 sm:flex-row">
                                    <button
                                        onClick={() => setIsUploadModalOpen(true)}
                                        className="inline-flex items-center justify-center gap-2 rounded-3xl bg-[#9d4300] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#b75b00]"
                                    >
                                        <span className="material-symbols-outlined text-base">upload_file</span>
                                        Tải lên cá nhân
                                    </button>
                                    <button
                                        onClick={() => setIsCreateFolderModalOpen(true)}
                                        className="inline-flex items-center justify-center gap-2 rounded-3xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                                    >
                                        <span className="material-symbols-outlined text-base">create_new_folder</span>
                                        Tạo thư mục cá nhân
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-12 gap-6">
                    <div className="col-span-12 lg:col-span-7 bg-white shadow-sm ring-1 ring-slate-100 rounded-3xl overflow-hidden">
                        <div className="border-b border-slate-100 px-5 py-4">
                            <h2 className="text-sm font-semibold text-slate-900">Thư mục & Tài liệu cá nhân</h2>
                            <p className="text-xs text-slate-500 mt-1">Hiển thị các thư mục và tài liệu với access_scope = "Cá nhân".</p>
                        </div>
                        <div className="p-4 space-y-2 max-h-[600px] overflow-y-auto">
                            {organizedData.folders.length === 0 && organizedData.unfoldered_documents.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-20 text-center gap-3 text-slate-500">
                                    <span className="material-symbols-outlined text-5xl">folder_open</span>
                                    <p className="text-sm font-semibold">Chưa có tài liệu cá nhân</p>
                                    <p className="text-xs max-w-xs">Bạn có thể tải lên tài liệu mới với access_scope "personal" từ trang Kho tài liệu.</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {/* Folders with documents */}
                                    {organizedData.folders.map((folder) => (
                                        <div key={folder.id} className="border border-slate-200 rounded-lg overflow-hidden">
                                            <button
                                                onClick={() => toggleFolder(folder.id)}
                                                className="w-full flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100 transition"
                                            >
                                                <div className="flex items-center gap-2">
                                                    <span className="material-symbols-outlined text-lg text-[#9d4300]">
                                                        {expandedFolders.has(folder.id) ? 'folder_open' : 'folder'}
                                                    </span>
                                                    <div className="text-left">
                                                        <p className="text-sm font-semibold text-slate-900">{folder.name}</p>
                                                        <p className="text-xs text-slate-500">{folder.documents.length} tài liệu</p>
                                                    </div>
                                                </div>
                                                <span className="material-symbols-outlined text-lg text-slate-400">
                                                    {expandedFolders.has(folder.id) ? 'expand_less' : 'expand_more'}
                                                </span>
                                            </button>

                                            {/* Documents in folder */}
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

                                    {/* Unfoldered documents */}
                                    {organizedData.unfoldered_documents.length > 0 && (
                                        <div className="border border-slate-200 rounded-lg overflow-hidden">
                                            <button
                                                onClick={() => toggleFolder('_unfoldered')}
                                                className="w-full flex items-center justify-between p-3 bg-amber-50 hover:bg-amber-100 transition"
                                            >
                                                <div className="flex items-center gap-2">
                                                    <span className="material-symbols-outlined text-lg text-amber-600">inbox</span>
                                                    <div className="text-left">
                                                        <p className="text-sm font-semibold text-slate-900">Tài liệu chưa phân loại</p>
                                                        <p className="text-xs text-slate-500">{organizedData.unfoldered_documents.length} tài liệu</p>
                                                    </div>
                                                </div>
                                                <span className="material-symbols-outlined text-lg text-slate-400">
                                                    {expandedFolders.has('_unfoldered') ? 'expand_less' : 'expand_more'}
                                                </span>
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

                    <DocumentSidebar
                        document={selectedDocument}
                        folder={selectedFolder}
                        onClose={clearSelection}
                    />
                </div>
                <UploadDocumentModal
                    isOpen={isUploadModalOpen}
                    onClose={() => setIsUploadModalOpen(false)}
                    onSuccess={() => void loadPersonalDocuments()}
                    defaultAccessScope="personal"
                    allowedScopes={['personal']}
                />
                <CreateFolderModal
                    isOpen={isCreateFolderModalOpen}
                    onClose={() => setIsCreateFolderModalOpen(false)}
                    onSuccess={() => void loadPersonalDocuments()}
                    defaultAccessScope="personal"
                    allowedScopes={['personal']}
                />
            </main>
        </div>
    )
}
