'use client'

/**
 * useDocumentStore - Hook quản lý state cho trang Document Store
 * 
 * Flow:
 *  1. Mount → fetchAllFolders() → build tree
 *  2. User expand folder → fetchFolderDocuments(folderId) → cache docs
 *  3. User select document → set selectedDocument for sidebar
 */



import { useState, useEffect, useCallback, useRef } from 'react'
import {
    fetchAllFolders,
    fetchFolderDocuments,
    fetchAllDocuments,
    FolderResponse,
    FolderDocumentResponse,
} from '@/services/folder'
import { ApiError } from '@/services/api'

// ─── Types ─────────────────────────────────────────────────

export interface FolderTreeNode {
    folder: FolderResponse
    children: FolderTreeNode[]
    documents: FolderDocumentResponse[]
    isExpanded: boolean
    isLoadingDocs: boolean
    hasLoadedDocs: boolean
}

/**
 * Represents documents not assigned to any folder
 * Grouped by: Department Documents, Personal Documents, Company Documents
 */
export interface OtherDocumentsNode {
    type: 'other-documents'
    label: string
    isExpanded: boolean
    isLoadingDocs: boolean
    hasLoadedDocs: boolean

    // Sub-categories
    departmentDocs: FolderDocumentResponse[]  // department != null, access_scope = department
    personalDocs: FolderDocumentResponse[]     // access_scope = personal, 
    companyDocs: FolderDocumentResponse[]      // access_scope = company,
}

export interface DocumentStoreState {
    /** Flat list of all folders */
    folders: FolderResponse[]
    /** Tree structure */
    tree: FolderTreeNode[]
    /** Documents not assigned to any folder */
    otherDocuments: OtherDocumentsNode
    /** Currently selected document */
    selectedDocument: FolderDocumentResponse | null
    /** Folder that contains the selected document */
    selectedFolder: FolderResponse | null
    /** Loading state for initial folder fetch */
    isLoading: boolean
    /** Error message */
    error: string | null
    /** Search query */
    searchQuery: string
}

interface UseDocumentStoreOptions {
    enabled?: boolean
    canReadFolders?: boolean
    canReadDocuments?: boolean
}

// ─── Helper: Flatten all sub_folders recursively ────────────

function flattenAllFolders(folders: FolderResponse[]): FolderResponse[] {
    const flattened: FolderResponse[] = []
    const seen = new Set<string>()

    function recursiveFlatten(items: FolderResponse[]) {
        items.forEach((folder) => {
            // Tránh duplicate
            if (seen.has(folder.id)) return
            seen.add(folder.id)

            // Thêm folder hiện tại (clear sub_folders để không bị lồng sâu)
            flattened.push({
                ...folder,
                sub_folders: undefined, // Remove nested structure
            } as FolderResponse)

            // Recursively flatten subfolder
            if (folder.sub_folders && folder.sub_folders.length > 0) {
                recursiveFlatten(folder.sub_folders)
            }
        })
    }

    recursiveFlatten(folders)
    return flattened
}

// ─── Helper: Categorize documents without folder ─────────────

function categorizeOtherDocuments(allDocs: FolderDocumentResponse[]): OtherDocumentsNode {
    const departmentDocs: FolderDocumentResponse[] = []
    const personalDocs: FolderDocumentResponse[] = []
    const companyDocs: FolderDocumentResponse[] = []

    // ✅ FIXED: Only process ROOT documents (folder_id = null)
    const rootDocs = allDocs.filter(doc => !doc.folder_id && !doc.folder)

    rootDocs.forEach((doc) => {
        const deptRef = doc.department ?? doc.department_id ?? null

        if (deptRef && doc.access_scope === 'department') {
            // Tài liệu Phòng ban: có department VÀ access_scope = department
            departmentDocs.push(doc)
        } else if (doc.access_scope === 'company') {
            // Tài liệu Công ty: access_scope = company (bất kể folder/department)
            companyDocs.push(doc)
        } else if (doc.access_scope === 'personal') {
            // Tài liệu Cá nhân: access_scope = personal (bất kể folder/department)
            personalDocs.push(doc)
        }
        // Các trường hợp khác không phân loại (bỏ qua)
    })

    return {
        type: 'other-documents',
        label: 'Tài liệu khác',
        isExpanded: false,
        isLoadingDocs: false,
        hasLoadedDocs: true,
        departmentDocs,
        personalDocs,
        companyDocs,
    }
}

// ─── Helper: Build tree from flat folder list ──────────────

function buildFolderTree(folders: FolderResponse[]): FolderTreeNode[] {
    // Bước 0: Flatten tất cả subfolder
    const flatFolders = flattenAllFolders(folders)

    const map = new Map<string, FolderTreeNode>()
    const roots: FolderTreeNode[] = []

    // Bước 1: Tạo map các node từ flat array
    flatFolders.forEach((folder) => {
        map.set(folder.id, {
            folder,
            children: [],
            documents: [],
            isExpanded: false,
            isLoadingDocs: false,
            hasLoadedDocs: false,
        })
    })

    // Bước 2: Xây dựng quan hệ cha-con dựa vào parent_id
    flatFolders.forEach((folder) => {
        const node = map.get(folder.id)!

        if (folder.parent_id && map.has(folder.parent_id)) {
            // Có parent → thêm vào parent.children
            const parentNode = map.get(folder.parent_id)!
            if (!parentNode.children.includes(node)) {
                parentNode.children.push(node)
            }
        } else if (!folder.parent_id) {
            // Không có parent → thêm vào roots
            roots.push(node)
        }
    })

    return roots
}

// ─── Helper: Deep clone tree with mutation ─────────────────

function updateTreeNode(
    tree: FolderTreeNode[],
    folderId: string,
    updater: (node: FolderTreeNode) => FolderTreeNode
): FolderTreeNode[] {
    return tree.map((node) => {
        if (node.folder.id === folderId) {
            return updater(node)
        }
        if (node.children.length > 0) {
            return {
                ...node,
                children: updateTreeNode(node.children, folderId, updater),
            }
        }
        return node
    })
}

function removeTreeNode(tree: FolderTreeNode[], folderId: string): FolderTreeNode[] {
    return tree
        .filter((node) => node.folder.id !== folderId)
        .map((node) => ({
            ...node,
            children: removeTreeNode(node.children, folderId),
        }))
}

// ─── Hook ──────────────────────────────────────────────────

export function useDocumentStore(options: UseDocumentStoreOptions = {}) {
    const enabled = options.enabled ?? true
    const canReadFolders = options.canReadFolders ?? true
    const canReadDocuments = options.canReadDocuments ?? true
    const [folders, setFolders] = useState<FolderResponse[]>([])
    const [tree, setTree] = useState<FolderTreeNode[]>([])
    const [otherDocuments, setOtherDocuments] = useState<OtherDocumentsNode>({
        type: 'other-documents',
        label: 'Tài liệu khác',
        isExpanded: false,
        isLoadingDocs: false,
        hasLoadedDocs: false,
        departmentDocs: [],
        personalDocs: [],
        companyDocs: [],
    })
    const [allDocuments, setAllDocuments] = useState<FolderDocumentResponse[]>([])
    const [selectedDocument, setSelectedDocument] = useState<FolderDocumentResponse | null>(null)
    const [selectedFolder, setSelectedFolder] = useState<FolderResponse | null>(null)
    const [isLoading, setIsLoading] = useState(enabled && (canReadFolders || canReadDocuments))
    const [error, setError] = useState<string | null>(null)
    const [searchQuery, setSearchQuery] = useState('')

    const hasLoadedRef = useRef(false)

    // ── Load all folders and other documents on mount ──────────────────────────
    const loadFolders = useCallback(async () => {
        if (!enabled || (!canReadFolders && !canReadDocuments)) {
            setIsLoading(false)
            setError(null)
            return
        }

        setIsLoading(true)
        setError(null)
        try {
            const [folderData, documentData] = await Promise.all([
                canReadFolders ? fetchAllFolders() : Promise.resolve([]),
                canReadDocuments
                    ? fetchAllDocuments({ page_size: 100, include_versions: true })
                    : Promise.resolve({ items: [], pagination: null }),
            ])

            setFolders(folderData)
            setTree(buildFolderTree(folderData))
            setAllDocuments(documentData.items)

            // Categorize documents not in any folder
            const otherDocs = categorizeOtherDocuments(documentData.items)
            setOtherDocuments(otherDocs)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Không thể tải danh sách thư mục'
            setError(message)
            console.warn('Failed to load folders:', err)
        } finally {
            setIsLoading(false)
        }
    }, [enabled, canReadFolders, canReadDocuments])

    useEffect(() => {
        if (!enabled || (!canReadFolders && !canReadDocuments)) {
            setIsLoading(false)
            setError(null)
            return
        }

        if (!hasLoadedRef.current) {
            hasLoadedRef.current = true
            loadFolders()
        }
    }, [enabled, canReadFolders, canReadDocuments, loadFolders])

    // ── Toggle folder expand/collapse ──────────────────────
    const toggleFolder = useCallback(async (folderId: string) => {
        setTree((prev) => {
            // Find the node to check if it's currently expanded
            const findNode = (nodes: FolderTreeNode[]): FolderTreeNode | null => {
                for (const n of nodes) {
                    if (n.folder.id === folderId) return n
                    const found = findNode(n.children)
                    if (found) return found
                }
                return null
            }

            const targetNode = findNode(prev)
            if (!targetNode) return prev

            // If collapsing, just toggle
            if (targetNode.isExpanded) {
                return updateTreeNode(prev, folderId, (node) => ({
                    ...node,
                    isExpanded: false,
                }))
            }

            // If expanding and docs already loaded, just expand
            if (targetNode.hasLoadedDocs) {
                return updateTreeNode(prev, folderId, (node) => ({
                    ...node,
                    isExpanded: true,
                }))
            }

            // Otherwise expand and set loading
            return updateTreeNode(prev, folderId, (node) => ({
                ...node,
                isExpanded: true,
                isLoadingDocs: canReadDocuments,
                hasLoadedDocs: canReadDocuments ? node.hasLoadedDocs : true,
            }))
        })

        // Check if we need to fetch documents
        const findNode = (nodes: FolderTreeNode[]): FolderTreeNode | null => {
            for (const n of nodes) {
                if (n.folder.id === folderId) return n
                const found = findNode(n.children)
                if (found) return found
            }
            return null
        }

        const currentTree = tree
        const targetNode = findNode(currentTree)

        // Only fetch documents if not already loaded and first time expanding
        if (targetNode && !targetNode.hasLoadedDocs && canReadDocuments) {
            try {
                const { items } = await fetchFolderDocuments(folderId, {
                    page_size: 50,
                    include_versions: true,
                })
                setTree((prev) =>
                    updateTreeNode(prev, folderId, (node) => ({
                        ...node,
                        documents: items,
                        isLoadingDocs: false,
                        hasLoadedDocs: true,
                    }))
                )
            } catch (err) {
                console.warn(`Failed to load documents for folder ${folderId}:`, err)
                const message = err instanceof ApiError
                    ? err.message || (err.data && (err.data as any).message) || `Server error ${(err as any).statusCode}`
                    : err instanceof Error
                        ? err.message
                        : 'Failed to load documents for folder'
                setError(message)
                setTree((prev) =>
                    updateTreeNode(prev, folderId, (node) => ({
                        ...node,
                        isLoadingDocs: false,
                    }))
                )
            }
        }
    }, [tree, canReadDocuments])

    // ── Toggle "Other Documents" section ───────────────────
    const toggleOtherDocuments = useCallback(() => {
        setOtherDocuments((prev) => ({
            ...prev,
            isExpanded: !prev.isExpanded,
        }))
    }, [])

    // ── Select a document ──────────────────────────────────
    const selectDocument = useCallback((doc: FolderDocumentResponse | null, folder?: FolderResponse) => {
        setSelectedDocument(doc)
        setSelectedFolder(folder || null)
    }, [])

    // ── Clear selection ────────────────────────────────────
    const clearSelection = useCallback(() => {
        setSelectedDocument(null)
        setSelectedFolder(null)
    }, [])

    const removeFolder = useCallback((folderId: string) => {
        setFolders((current) => current.filter((folder) => folder.id !== folderId))
        setTree((current) => removeTreeNode(current, folderId))
    }, [])

    // ── Stats ──────────────────────────────────────────────
    const getStats = useCallback(() => {
        if (allDocuments.length > 0) {
            return {
                totalFolders: folders.length,
                totalDocuments: allDocuments.length,
            }
        }

        let totalDocuments = 0

        // Count documents in folders
        const countDocs = (nodes: FolderTreeNode[]) => {
            nodes.forEach((n) => {
                totalDocuments += n.documents.length
                countDocs(n.children)
            })
        }
        countDocs(tree)

        // Count other documents
        totalDocuments +=
            otherDocuments.departmentDocs.length +
            otherDocuments.personalDocs.length +
            otherDocuments.companyDocs.length

        return {
            totalFolders: folders.length,
            totalDocuments,
        }
    }, [folders, tree, otherDocuments, allDocuments])

    return {
        folders,
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
        selectDocument,
        clearSelection,
        removeFolder,
        refetch: loadFolders,
        getStats,
    }
}
