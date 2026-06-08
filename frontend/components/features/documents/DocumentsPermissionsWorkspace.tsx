'use client'

import { AppIcon } from '@/components/ui/AppIcon'
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { DocumentPermissionsPanel } from './DocumentPermissionsPanel'
import { FolderTreeNode, OtherDocumentsNode } from '@/hooks/useDocumentStore'
import { FolderDocumentResponse, FolderResponse, FolderWithDocuments, SharedDocumentsOrganized } from '@/services/folder'
import { DocumentRow } from './DocumentRow'
import {
    fetchAllDocumentPermissions,
    fetchAllFolderPermissions,
    DocumentPermissionsListEntry,
    FolderPermissionsListEntry,
    PermissionItem,
} from '@/services/documentAcl'
import { useAuthContext } from '@/context'
import { useRBAC } from '@/hooks/useRBAC'

interface DocumentsPermissionsWorkspaceProps {
    tree: FolderTreeNode[]
    otherDocuments: OtherDocumentsNode
    allDocuments: FolderDocumentResponse[]
    sharedWithMe: SharedDocumentsOrganized
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

function flattenSharedFolders(nodes: FolderWithDocuments[]): FolderWithDocuments[] {
    const result: FolderWithDocuments[] = []
    const seen = new Set<string>()

    const walk = (items: FolderWithDocuments[]) => {
        items.forEach((folder) => {
            if (!folder?.id || seen.has(folder.id)) return
            seen.add(folder.id)
            result.push(folder)

            if (Array.isArray(folder.sub_folders) && folder.sub_folders.length > 0) {
                walk(folder.sub_folders as FolderWithDocuments[])
            }
        })
    }

    walk(nodes)
    return result
}

function flattenSharedDocuments(
    sharedWithMe: SharedDocumentsOrganized,
    folderMap: Map<string, FolderResponse>
): FlatDocumentItem[] {
    const result: FlatDocumentItem[] = []
    const seen = new Set<string>()

    const addDocument = (document: FolderDocumentResponse, folder: FolderResponse | null) => {
        if (!document?.id || seen.has(document.id)) return
        seen.add(document.id)
        result.push({ document, folder })
    }

    const walk = (folders: FolderWithDocuments[]) => {
        folders.forEach((folder) => {
            const mappedFolder = folderMap.get(folder.id) ?? folder
            folder.documents?.forEach((document) => addDocument(document, mappedFolder))
            if (Array.isArray(folder.sub_folders) && folder.sub_folders.length > 0) {
                walk(folder.sub_folders as FolderWithDocuments[])
            }
        })
    }

    walk(sharedWithMe.folders)
    sharedWithMe.unfoldered_documents.forEach((document) => addDocument(document, null))
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
                    <AppIcon name="folder" className={`text-lg ${selected ? 'text-[#9d4300]' : 'text-[#9d4300]'}`} />
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
                            <AppIcon name="folder_open" className="text-[10px]" />
                            {toSafeCount(item.folder.subfolder_count)} thư mục con
                        </span>
                        <button
                            onClick={onViewDetails}
                            className="inline-flex items-center gap-1 rounded-full bg-[#9d4300] px-2.5 py-0.5 text-[9px] font-bold text-white transition-colors hover:bg-[#b75b00]"
                        >
                            <AppIcon name="visibility" className="text-[10px]" />
                            Xem chi tiết
                        </button>
                        <button
                            onClick={onSelect}
                            className="inline-flex items-center gap-1 rounded-full bg-white px-2.5 py-0.5 text-[9px] font-bold text-[#9d4300] ring-1 ring-[#9d4300]/20 transition-colors hover:bg-[#fff3e0]"
                        >
                            <AppIcon name="check_circle" className="text-[10px]" />
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
                        <AppIcon name="visibility" className="text-[14px]" />
                        Xem chi tiết
                    </button>
                    <button
                        onClick={onSelect}
                        className="inline-flex items-center gap-1 rounded-lg border border-[#9d4300]/20 bg-white px-2.5 py-1.5 text-[10px] font-bold text-[#9d4300] transition-colors hover:bg-[#fff3e0]"
                    >
                        <AppIcon name="check_circle" className="text-[14px]" />
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
    allDocuments,
    sharedWithMe,
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
    const { user } = useAuthContext()
    const { hasAnyPermission } = useRBAC()
    const canManageFolderPermissions = hasAnyPermission(['folder_update', 'folder_delete'])
    const canManageDocumentPermissions = hasAnyPermission(['document_share', 'document_update', 'document_delete'])

    const folders = useMemo(() => flattenFolders(tree), [tree])
    const folderMap = useMemo(() => {
        const map = new Map<string, FolderResponse>()
        folders.forEach((item) => {
            map.set(item.folder.id, item.folder)
        })
        return map
    }, [folders])

    const documents = useMemo(() => {
        const seen = new Set<string>()

        return allDocuments
            .map((document) => {
                const folderId = document.folder || document.folder_id || null
                const folder = folderId ? folderMap.get(folderId) ?? null : null
                return { document, folder }
            })
            .filter((entry) => {
                if (!entry.document?.id) return false
                if (seen.has(entry.document.id)) return false
                seen.add(entry.document.id)
                return true
            })
    }, [allDocuments, folderMap])

    const sharedFolders = useMemo(() => flattenSharedFolders(sharedWithMe.folders), [sharedWithMe.folders])
    const sharedDocuments = useMemo(() => flattenSharedDocuments(sharedWithMe, folderMap), [sharedWithMe, folderMap])

    const allPermissionResources = useMemo<PermissionResourceOption[]>(() => {
        const folderOptions = folders.map((item) => ({
            key: `folder:${item.folder.id}` as PermissionResourceKey,
            kind: 'folder' as const,
            label: `${item.folder.name} · Folder`,
            folder: item.folder,
            document: null,
        }))

        const sharedFolderOptions = sharedFolders.map((folder) => ({
            key: `folder:${folder.id}` as PermissionResourceKey,
            kind: 'folder' as const,
            label: `${folder.name} · Folder`,
            folder,
            document: null,
        }))

        const documentOptions = documents.map((item) => ({
            key: `document:${item.document.id}` as PermissionResourceKey,
            kind: 'document' as const,
            label: `${item.document.original_name || item.document.filename} · Document`,
            folder: item.folder,
            document: item.document,
        }))

        const sharedDocumentOptions = sharedDocuments.map((item) => ({
            key: `document:${item.document.id}` as PermissionResourceKey,
            kind: 'document' as const,
            label: `${item.document.original_name || item.document.filename} · Document`,
            folder: item.folder,
            document: item.document,
        }))

        const uniqueResources = new Map<string, PermissionResourceOption>()
            ;[...folderOptions, ...sharedFolderOptions, ...documentOptions, ...sharedDocumentOptions].forEach((resource) => {
                if (!uniqueResources.has(resource.key)) {
                    uniqueResources.set(resource.key, resource)
                }
            })

        return Array.from(uniqueResources.values()).filter((resource) => (
            resource.kind === 'folder' ? canManageFolderPermissions : canManageDocumentPermissions
        ))
    }, [documents, folders, sharedDocuments, sharedFolders, canManageFolderPermissions, canManageDocumentPermissions])

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
            const grantedById = user?.account_id || user?.id
            const [folderItems, documentItems] = await Promise.all([
                canManageFolderPermissions
                    ? loadAllPages((page, pageSize) => fetchAllFolderPermissions(page, pageSize, '', grantedById))
                    : Promise.resolve([]),
                canManageDocumentPermissions
                    ? loadAllPages((page, pageSize) => fetchAllDocumentPermissions(page, pageSize, '', grantedById))
                    : Promise.resolve([]),
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
    }, [canManageFolderPermissions, canManageDocumentPermissions, user?.account_id, user?.id])

    useEffect(() => {
        void loadOverview()

    }, [loadOverview])

    useEffect(() => {
        if (resourceKind === 'folder' && !canManageFolderPermissions && canManageDocumentPermissions) {
            setResourceKind('document')
            setSelectedFolderId(null)
        }
        if (resourceKind === 'document' && !canManageDocumentPermissions && canManageFolderPermissions) {
            setResourceKind('folder')
            setSelectedDocumentId(null)
        }
    }, [resourceKind, canManageFolderPermissions, canManageDocumentPermissions])

    const showFolder = resourceKind === 'folder'
    const panelFolder = showFolder ? currentFolder : currentDocumentEntry?.folder || null
    const panelDocument = showFolder ? null : currentDocumentEntry?.document || null

    const openDetails = (target: DetailTarget) => {
        if (target.kind === 'folder') {
            if (!canManageFolderPermissions) return
            setDialogMode('detail')
            setResourceKind('folder')
            setSelectedFolderId(target.folder.id)
            setPermissionResourceKey(`folder:${target.folder.id}`)
            setIsPermissionDialogOpen(true)
        } else {
            if (!canManageDocumentPermissions) return
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
                            onClick={() => canManageFolderPermissions && openFolderPermission()}
                            disabled={!canManageFolderPermissions}
                            className="inline-flex items-center gap-1.5 rounded-full bg-[#9d4300] px-3 py-2 text-[11px] font-bold text-white transition-colors hover:bg-[#b75b00]"
                        >
                            <AppIcon name="folder" className="text-[14px]" />
                            Cấp quyền thư mục
                        </button>
                        <button
                            type="button"
                            onClick={() => canManageDocumentPermissions && openDocumentPermission()}
                            disabled={!canManageDocumentPermissions}
                            className="inline-flex items-center gap-1.5 rounded-full border border-[#9d4300]/20 bg-white px-3 py-2 text-[11px] font-bold text-[#9d4300] transition-colors hover:bg-[#fff3e0]"
                        >
                            <AppIcon name="description" className="text-[14px]" />
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
                                    <AppIcon name="close" className="text-[18px]" />
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
