'use client'

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { DocumentPermissionsPanel } from './DocumentPermissionsPanel'
import { FolderTreeNode, OtherDocumentsNode } from '@/hooks/useDocumentStore'
import { FolderDocumentResponse, FolderResponse } from '@/services/folder'
import { DocumentRow } from './DocumentRow'
import {
    fetchAllDocumentPermissions,
    fetchAllFolderPermissions,
    DocumentPermissionsListEntry,
    FolderPermissionsListEntry,
    PermissionItem,
} from '@/services/documentAcl'

interface DocumentsPermissionsWorkspaceProps {
    tree: FolderTreeNode[]
    otherDocuments: OtherDocumentsNode
    selectedDocument: FolderDocumentResponse | null
    selectedFolder: FolderResponse | null
    onSelectDocument: (doc: FolderDocumentResponse, folder?: FolderResponse) => void
}

type ResourceKind = 'folder' | 'document'

type PermissionResourceKey = `folder:${string}` | `document:${string}`

type PermissionResourceOption = {
    key: PermissionResourceKey
    kind: ResourceKind
    label: string
    folder: FolderResponse | null
    document: FolderDocumentResponse | null
}

type FlatFolderItem = {
    folder: FolderResponse
    depth: number
}

type FlatDocumentItem = {
    document: FolderDocumentResponse
    folder: FolderResponse | null
}

type DetailTarget =
    | { kind: 'folder'; folder: FolderResponse }
    | { kind: 'document'; document: FolderDocumentResponse; folder: FolderResponse | null }

type OverviewState = {
    loading: boolean
    error: string | null
    folderItems: FolderPermissionsListEntry[]
    documentItems: DocumentPermissionsListEntry[]
}

function toSafeCount(value: unknown): number {
    const count = Number(value)
    return Number.isFinite(count) && count > 0 ? count : 0
}

function sumSafeCounts(items: Array<{ total_permissions?: unknown }>): number {
    return items.reduce((sum, item) => sum + toSafeCount(item.total_permissions), 0)
}

function flattenFolders(nodes: FolderTreeNode[], depth = 0): FlatFolderItem[] {
    const result: FlatFolderItem[] = []

    nodes.forEach((node) => {
        result.push({ folder: node.folder, depth })
        if (node.children.length > 0) {
            result.push(...flattenFolders(node.children, depth + 1))
        }
    })

    return result
}

function collectTreeDocuments(nodes: FolderTreeNode[]): FlatDocumentItem[] {
    const result: FlatDocumentItem[] = []

    nodes.forEach((node) => {
        node.documents.forEach((document) => {
            result.push({ document, folder: node.folder })
        })
        if (node.children.length > 0) {
            result.push(...collectTreeDocuments(node.children))
        }
    })

    return result
}

function FolderCard({
    item,
    selected,
    onSelect,
    onViewDetails,
}: {
    item: FlatFolderItem
    selected: boolean
    onSelect: () => void
    onViewDetails: () => void
}) {
    return (
        <div
            className={`w-full rounded-xl border px-3 py-3 text-left transition-all ${selected
                ? 'border-[#f97316]/30 bg-[#fef5ed] shadow-sm'
                : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                }`}
            style={{ marginLeft: `${item.depth * 14}px` }}
        >
            <div className="flex items-start gap-2.5">
                <div className={`mt-0.5 flex h-9 w-9 items-center justify-center rounded-lg ${selected ? 'bg-white' : 'bg-[#fff3e0]'}`}>
                    <span className={`material-symbols-outlined text-lg ${selected ? 'text-[#9d4300]' : 'text-[#9d4300]'}`}>folder</span>
                </div>
                <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                            <p className={`truncate text-[13px] font-bold ${selected ? 'text-[#9d4300]' : 'text-slate-800'}`}>{item.folder.name}</p>
                            <p className="mt-0.5 text-[10px] capitalize text-slate-400">{item.folder.access_scope}</p>
                        </div>
                        <span className="rounded-full bg-white px-2 py-0.5 text-[9px] font-bold text-slate-500 ring-1 ring-slate-200">
                            {toSafeCount(item.folder.document_count)} tài liệu
                        </span>
                    </div>
                    {item.folder.description && (
                        <p className="mt-1.5 line-clamp-2 text-[10px] text-slate-500">{item.folder.description}</p>
                    )}
                    <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                        <span className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[9px] font-semibold text-slate-500 ring-1 ring-slate-200">
                            <span className="material-symbols-outlined text-[10px]">folder_open</span>
                            {toSafeCount(item.folder.subfolder_count)} thư mục con
                        </span>
                        <button
                            onClick={onViewDetails}
                            className="inline-flex items-center gap-1 rounded-full bg-[#9d4300] px-2.5 py-0.5 text-[9px] font-bold text-white transition-colors hover:bg-[#b75b00]"
                        >
                            <span className="material-symbols-outlined text-[10px]">visibility</span>
                            Xem chi tiết
                        </button>
                        <button
                            onClick={onSelect}
                            className="inline-flex items-center gap-1 rounded-full bg-white px-2.5 py-0.5 text-[9px] font-bold text-[#9d4300] ring-1 ring-[#9d4300]/20 transition-colors hover:bg-[#fff3e0]"
                        >
                            <span className="material-symbols-outlined text-[10px]">check_circle</span>
                            Chọn nhanh
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

function DocumentCard({
    item,
    selected,
    onSelect,
    onViewDetails,
}: {
    item: FlatDocumentItem
    selected: boolean
    onSelect: () => void
    onViewDetails: () => void
}) {
    const folderName = item.folder?.name
    const departmentName = item.folder?.department_id ? undefined : undefined

    return (
        <div className={`rounded-xl border p-2.5 transition-all ${selected ? 'border-[#f97316]/30 bg-[#fef5ed]' : 'border-slate-200 bg-white hover:bg-slate-50'}`}>
            <div className="flex items-start gap-2.5">
                <div className="flex-1 min-w-0">
                    <DocumentRow
                        document={item.document}
                        isSelected={selected}
                        onSelect={onSelect}
                        folderName={folderName || undefined}
                        departmentName={departmentName}
                    />
                </div>
                <div className="mt-1 flex flex-col gap-2">
                    <button
                        onClick={onViewDetails}
                        className="inline-flex items-center gap-1 rounded-lg bg-[#9d4300] px-2.5 py-1.5 text-[10px] font-bold text-white transition-colors hover:bg-[#b75b00]"
                    >
                        <span className="material-symbols-outlined text-[14px]">visibility</span>
                        Xem chi tiết
                    </button>
                    <button
                        onClick={onSelect}
                        className="inline-flex items-center gap-1 rounded-lg border border-[#9d4300]/20 bg-white px-2.5 py-1.5 text-[10px] font-bold text-[#9d4300] transition-colors hover:bg-[#fff3e0]"
                    >
                        <span className="material-symbols-outlined text-[14px]">check_circle</span>
                        Chọn nhanh
                    </button>
                </div>
            </div>
        </div>
    )
}

function PermissionOverviewCard({
    title,
    total,
    items,
    onViewDetails,
}: {
    title: string
    subtitle: string
    total: number
    items: Array<FolderPermissionsListEntry | DocumentPermissionsListEntry>
    onViewDetails: (target: DetailTarget) => void
}) {
    return (
        <div className="rounded-[1.5rem] border border-slate-100 bg-white shadow-sm overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <div>
                    <h3 className="text-[13px] font-extrabold text-slate-900">{title}</h3>

                </div>

            </div>

            <div className="max-h-[420px] space-y-2 overflow-y-auto p-3">
                {items.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-[11px] text-slate-400">
                        Chưa có dữ liệu quyền.
                    </div>
                ) : (
                    items.map((item) => {
                        const resourceId = 'folder_id' in item ? item.folder_id : item.document_id
                        const resourceTitle = 'folder_name' in item ? item.folder_name : item.document_name
                        const permissionCount = item.permissions?.length || 0
                        const previewPermissions = item.permissions.slice(0, 3)
                        const firstPermission = item.permissions[0] as PermissionItem | undefined

                        return (
                            <div key={resourceId} className="rounded-xl border border-slate-200 bg-slate-50/50 px-3 py-3">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <p className="truncate text-[13px] font-bold text-slate-800">{resourceTitle}</p>
                                        <p className="mt-0.5 text-[10px] capitalize text-slate-400">{item.access_scope}</p>
                                    </div>
                                    <span className="rounded-full bg-white px-2 py-0.5 text-[9px] font-bold text-slate-500 ring-1 ring-slate-200">
                                        {permissionCount} quyền
                                    </span>
                                </div>

                                <div className="mt-2 space-y-1.5">
                                    {previewPermissions.length > 0 ? (
                                        previewPermissions.map((perm) => (
                                            <div key={perm.id} className="flex items-center justify-between gap-3 rounded-lg bg-white px-2.5 py-2 text-[11px] ring-1 ring-slate-100">
                                                <div className="min-w-0">
                                                    <p className="truncate font-semibold text-slate-700">{perm.subject_name || perm.subject_id}</p>
                                                </div>
                                                <span className="rounded-full bg-[#fef5ed] px-2 py-0.5 text-[9px] font-bold text-[#9d4300]">{perm.permission}</span>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="rounded-lg border border-dashed border-slate-200 bg-white px-2.5 py-3 text-center text-[11px] text-slate-400">
                                            Không có permission nào
                                        </div>
                                    )}
                                </div>

                                <div className="mt-2 flex items-center justify-between gap-2">
                                    <p className="text-[10px] text-slate-400">
                                        {firstPermission?.created_at ? `Tạo lúc: ${new Date(firstPermission.created_at).toLocaleDateString('vi-VN')}` : 'Chưa có dữ liệu chi tiết'}
                                    </p>
                                    {'folder_id' in item ? (
                                        <button
                                            onClick={() => onViewDetails({ kind: 'folder', folder: { id: item.folder_id, name: item.folder_name, access_scope: item.access_scope } as FolderResponse })}
                                            className="inline-flex items-center gap-1 rounded-full bg-[#9d4300] px-2.5 py-1 text-[9px] font-bold text-white transition-colors hover:bg-[#b75b00]"
                                        >
                                            Xem chi tiết
                                        </button>
                                    ) : (
                                        <button
                                            onClick={() => onViewDetails({ kind: 'document', document: { id: item.document_id, original_name: item.document_name, filename: item.document_name } as FolderDocumentResponse, folder: null })}
                                            className="inline-flex items-center gap-1 rounded-full bg-[#9d4300] px-2.5 py-1 text-[9px] font-bold text-white transition-colors hover:bg-[#b75b00]"
                                        >
                                            Xem chi tiết
                                        </button>
                                    )}
                                </div>
                            </div>
                        )
                    })
                )}
            </div>
        </div>
    )
}

export function DocumentsPermissionsWorkspace({
    tree,
    otherDocuments,
    selectedDocument,
    selectedFolder,
    onSelectDocument,
}: DocumentsPermissionsWorkspaceProps) {
    const [resourceKind, setResourceKind] = useState<ResourceKind>('folder')
    const [permissionResourceKey, setPermissionResourceKey] = useState<PermissionResourceKey | ''>('')
    const [dialogMode, setDialogMode] = useState<'create' | 'detail'>('create')
    const [selectedFolderId, setSelectedFolderId] = useState<string | null>(selectedFolder?.id || null)
    const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(selectedDocument?.id || null)
    const [isPermissionDialogOpen, setIsPermissionDialogOpen] = useState(false)
    const [overview, setOverview] = useState<OverviewState>({
        loading: false,
        error: null,
        folderItems: [],
        documentItems: [],
    })

    const folders = useMemo(() => flattenFolders(tree), [tree])
    const treeDocuments = useMemo(() => collectTreeDocuments(tree), [tree])
    const otherDocumentsList = useMemo(() => {
        return [
            ...otherDocuments.departmentDocs.map((document) => ({ document, folder: null })),
            ...otherDocuments.personalDocs.map((document) => ({ document, folder: null })),
            ...otherDocuments.companyDocs.map((document) => ({ document, folder: null })),
        ]
    }, [otherDocuments])

    const documents = useMemo(() => {
        const seen = new Set<string>()
        const allDocuments = [...treeDocuments, ...otherDocumentsList]
        return allDocuments.filter((entry) => {
            if (seen.has(entry.document.id)) return false
            seen.add(entry.document.id)
            return true
        })
    }, [treeDocuments, otherDocumentsList])

    const allPermissionResources = useMemo<PermissionResourceOption[]>(() => {
        const folderOptions = folders.map((item) => ({
            key: `folder:${item.folder.id}` as PermissionResourceKey,
            kind: 'folder' as const,
            label: `${item.folder.name} · Folder`,
            folder: item.folder,
            document: null,
        }))

        const documentOptions = documents.map((item) => ({
            key: `document:${item.document.id}` as PermissionResourceKey,
            kind: 'document' as const,
            label: `${item.document.original_name || item.document.filename} · Document`,
            folder: item.folder,
            document: item.document,
        }))

        return [...folderOptions, ...documentOptions]
    }, [documents, folders])

    const currentFolder = useMemo(
        () => folders.find((item) => item.folder.id === selectedFolderId)?.folder || null,
        [folders, selectedFolderId]
    )

    const currentDocumentEntry = useMemo(
        () => documents.find((item) => item.document.id === selectedDocumentId) || null,
        [documents, selectedDocumentId]
    )

    const dialogPermissionResources = dialogMode === 'detail' ? allPermissionResources : allPermissionResources

    const applyPermissionResource = (resource: PermissionResourceOption | null) => {
        if (!resource) return

        setPermissionResourceKey(resource.key)
        setResourceKind(resource.kind)
        setSelectedFolderId(resource.folder?.id || null)
        setSelectedDocumentId(resource.document?.id || null)
    }

    const openFolderPermission = () => {
        setDialogMode('create')
        setResourceKind('folder')
        setPermissionResourceKey('')
        setSelectedFolderId(null)
        setSelectedDocumentId(null)
        setIsPermissionDialogOpen(true)
    }

    const openDocumentPermission = () => {
        setDialogMode('create')
        setResourceKind('document')
        setPermissionResourceKey('')
        setSelectedFolderId(null)
        setSelectedDocumentId(null)
        setIsPermissionDialogOpen(true)
    }

    useEffect(() => {
        if (selectedFolder?.id) {
            setSelectedFolderId(selectedFolder.id)
            setResourceKind('folder')
        }
    }, [selectedFolder?.id])

    useEffect(() => {
        if (selectedDocument?.id) {
            setSelectedDocumentId(selectedDocument.id)
        }
    }, [selectedDocument?.id])

    const loadOverview = useCallback(async () => {
        const loadAllPages = async <T,>(loader: (page: number, pageSize: number) => Promise<{ items: T[]; pagination: { has_next: boolean } }>) => {
            const collected: T[] = []
            let page = 1
            let hasNext = true

            while (hasNext) {
                const response = await loader(page, 100)
                collected.push(...response.items)
                hasNext = response.pagination.has_next
                page += 1
            }

            return collected
        }

        setOverview((prev) => ({ ...prev, loading: true, error: null }))

        try {
            const [folderItems, documentItems] = await Promise.all([
                loadAllPages((page, pageSize) => fetchAllFolderPermissions(page, pageSize)),
                loadAllPages((page, pageSize) => fetchAllDocumentPermissions(page, pageSize)),
            ])

            setOverview({
                loading: false,
                error: null,
                folderItems,
                documentItems,
            })
        } catch (error) {
            setOverview({
                loading: false,
                error: error instanceof Error ? error.message : 'Không thể tải ACL overview',
                folderItems: [],
                documentItems: [],
            })
        }
    }, [])

    useEffect(() => {
        void loadOverview()

    }, [loadOverview])

    const showFolder = resourceKind === 'folder'
    const panelFolder = showFolder ? currentFolder : currentDocumentEntry?.folder || null
    const panelDocument = showFolder ? null : currentDocumentEntry?.document || null

    const openDetails = (target: DetailTarget) => {
        if (target.kind === 'folder') {
            setDialogMode('detail')
            setResourceKind('folder')
            setSelectedFolderId(target.folder.id)
            setPermissionResourceKey(`folder:${target.folder.id}`)
            setIsPermissionDialogOpen(true)
        } else {
            setDialogMode('detail')
            setResourceKind('document')
            setSelectedDocumentId(target.document.id)
            setPermissionResourceKey(`document:${target.document.id}`)
            onSelectDocument(target.document, target.folder || undefined)
            setIsPermissionDialogOpen(true)
        }
    }

    return (
        <div className="space-y-3">

            <div className="rounded-[1.5rem] border border-slate-100 bg-white p-4 shadow-sm">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">Quick ACL actions</p>
                        <h3 className="mt-1 text-[14px] font-extrabold text-slate-900">Cấp quyền nhanh cho folder hoặc document</h3>
                        <p className="mt-1 text-[11px] text-slate-500">Chọn đúng ngữ cảnh rồi dùng form bên dưới để add permission.</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <button
                            type="button"
                            onClick={openFolderPermission}
                            className="inline-flex items-center gap-1.5 rounded-full bg-[#9d4300] px-3 py-2 text-[11px] font-bold text-white transition-colors hover:bg-[#b75b00]"
                        >
                            <span className="material-symbols-outlined text-[14px]">folder</span>
                            Cấp quyền thư mục
                        </button>
                        <button
                            type="button"
                            onClick={openDocumentPermission}
                            className="inline-flex items-center gap-1.5 rounded-full border border-[#9d4300]/20 bg-white px-3 py-2 text-[11px] font-bold text-[#9d4300] transition-colors hover:bg-[#fff3e0]"
                        >
                            <span className="material-symbols-outlined text-[14px]">description</span>
                            Cấp quyền tài liệu
                        </button>
                    </div>
                </div>
            </div>

            {isPermissionDialogOpen && (
                <>
                    <div
                        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
                        onClick={() => setIsPermissionDialogOpen(false)}
                    />
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
                        <div
                            className="w-full max-w-5xl rounded-2xl bg-white shadow-2xl"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
                                <div>
                                    <h3 className="mt-1 text-[15px] font-extrabold text-slate-900">
                                        {dialogMode === 'detail'
                                            ? (showFolder ? 'Cấp quyền thư mục' : 'Cấp quyền tài liệu')
                                            : (showFolder ? 'Thêm quyền cho thư mục' : 'Thêm quyền cho tài liệu')}
                                    </h3>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setIsPermissionDialogOpen(false)}
                                    className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-700"
                                    aria-label="Close dialog"
                                >
                                    <span className="material-symbols-outlined text-[18px]">close</span>
                                </button>
                            </div>

                            <div className="max-h-[85vh] overflow-y-auto p-4 md:p-5">
                                <div className="mb-4 rounded-2xl border border-slate-100 bg-slate-50 p-4 shadow-sm">
                                    <div className="space-y-2">
                                        <div>
                                            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">Chọn nguồn cấp quyền</p>
                                            <p className="mt-1 text-[12px] text-slate-500">Danh sách bên dưới gồm tất cả thư mục và tài liệu trong hệ thống.</p>
                                        </div>

                                        <select
                                            value={permissionResourceKey}
                                            disabled={dialogMode === 'detail'}
                                            onChange={(e) => {
                                                const selectedKey = e.target.value as PermissionResourceKey | ''
                                                setPermissionResourceKey(selectedKey)

                                                const resource = allPermissionResources.find((item) => item.key === selectedKey)
                                                if (resource) {
                                                    setResourceKind(resource.kind)
                                                    setSelectedFolderId(resource.folder?.id || null)
                                                    setSelectedDocumentId(resource.document?.id || null)
                                                } else {
                                                    setSelectedFolderId(null)
                                                    setSelectedDocumentId(null)
                                                }
                                            }}
                                            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-[13px] text-slate-700 outline-none transition focus:border-[#9d4300]"
                                        >
                                            <option value="">
                                                {dialogMode === 'detail'
                                                    ? 'Đang xem chi tiết tài nguyên đã chọn'
                                                    : 'Chọn thư mục/tài liệu'}
                                            </option>
                                            <optgroup label="Folder">
                                                {dialogPermissionResources
                                                    .filter((item) => item.kind === 'folder')
                                                    .map((item) => (
                                                        <option key={item.key} value={item.key}>
                                                            {item.label}
                                                        </option>
                                                    ))}
                                            </optgroup>
                                            <optgroup label="Document">
                                                {dialogPermissionResources
                                                    .filter((item) => item.kind === 'document')
                                                    .map((item) => (
                                                        <option key={item.key} value={item.key}>
                                                            {item.label}
                                                        </option>
                                                    ))}
                                            </optgroup>
                                        </select>

                                        {dialogMode === 'create' && allPermissionResources.length === 0 && (
                                            <p className="text-[11px] text-amber-600">Chưa có folder hoặc document nào trong hệ thống.</p>
                                        )}
                                    </div>
                                </div>

                                <DocumentPermissionsPanel
                                    folder={panelFolder}
                                    document={panelDocument}
                                    mode={dialogMode}
                                    onPermissionChanged={loadOverview}
                                    onPermissionGranted={() => setIsPermissionDialogOpen(false)}
                                    title={showFolder
                                        ? currentFolder?.name || panelFolder?.name || 'Cấp quyền thư mục'
                                        : currentDocumentEntry?.document.original_name || currentDocumentEntry?.document.filename || 'Cấp quyền tài liệu'}
                                />
                            </div>
                        </div>
                    </div>
                </>
            )}

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                <PermissionOverviewCard
                    title="Danh sách quyền thư mục"
                    subtitle="Toàn bộ folder_permission lấy từ API getall"
                    total={sumSafeCounts(overview.folderItems)}
                    items={overview.folderItems}
                    onViewDetails={openDetails}
                />
                <PermissionOverviewCard
                    title="Danh sách quyền tài liệu"
                    subtitle="Toàn bộ document_permission lấy từ API getall"
                    total={sumSafeCounts(overview.documentItems)}
                    items={overview.documentItems}
                    onViewDetails={openDetails}
                />
            </div>

            {overview.loading && (
                <div className="rounded-xl border border-slate-100 bg-white px-4 py-3 text-[12px] text-slate-500 shadow-sm">
                    Đang tải toàn bộ permission từ backend...
                </div>
            )}

            {overview.error && (
                <div className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-[12px] text-red-700">
                    {overview.error}
                </div>
            )}

        </div>
    )
}
