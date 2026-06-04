import { useEffect, useState, useCallback } from 'react';
import { FolderDetail } from '@/types/folders';
import { api } from '@/services/api/client';
import { fetchAllFolders, FolderResponse } from '@/services/folder';

export interface DocumentNode {
    id: string;
    filename: string;
    original_name?: string;
    file_type: string;
    file_size: number;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    created_at: string;
    updated_at: string;
    access_scope: 'PUBLIC' | 'PRIVATE';
    uploader?: any;
    folder_id?: string | null;
    folder?: string | null;
    department?: string | null;
    department_id?: string | null;
}

export interface FolderTreeNode extends FolderResponse {
    subFolders: FolderTreeNode[];
    documents: DocumentNode[];
    expanded?: boolean;
    totalFiles?: number;
}

interface UseDepartmentFoldersResult {
    folders: FolderTreeNode[];
    loading: boolean;
    error: string | null;
    selectedFolder: FolderTreeNode | null;
    selectedDocument: DocumentNode | null;
    selectFolder: (folder: FolderTreeNode | null) => void;
    selectDocument: (document: DocumentNode | null) => void;
    toggleFolder: (folderId: string) => void;
    refresh: () => Promise<void>;
}

interface UseDepartmentFoldersOptions {
    enabled?: boolean;
    canReadFolders?: boolean;
    canReadDocuments?: boolean;
}

export function useDepartmentFolders(
    deptId: string,
    options: UseDepartmentFoldersOptions = {}
): UseDepartmentFoldersResult {
    const enabled = options.enabled ?? true;
    const canReadFolders = options.canReadFolders ?? true;
    const canReadDocuments = options.canReadDocuments ?? true;
    const [folders, setFolders] = useState<FolderTreeNode[]>([]);
    const [loading, setLoading] = useState(enabled && !!deptId && canReadFolders && canReadDocuments);
    const [error, setError] = useState<string | null>(null);
    const [selectedFolder, setSelectedFolder] = useState<FolderTreeNode | null>(null);
    const [selectedDocument, setSelectedDocument] = useState<DocumentNode | null>(null);

    const fetchFolders = useCallback(async () => {
        if (!enabled || !deptId || !canReadFolders || !canReadDocuments) {
            setFolders([]);
            setError(null);
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            setError(null);

            // The core issue is that the department-specific API does not return subfolders.
            // We use the global folders API which returns a complete NESTED tree.
            const allFolders = await fetchAllFolders();

            // Fetch documents for department
            const docsResponse = await api.get<any>(
                `/departments/${deptId}/documents?page=1&page_size=1000`
            );

            const documents: DocumentNode[] = docsResponse.data?.items || [];

            // Helper to recursively map FolderResponse to FolderTreeNode and assign documents
            const mapToTreeNode = (folder: FolderResponse): FolderTreeNode => {
                const node: FolderTreeNode = {
                    ...folder,
                    subFolders: (folder.sub_folders || []).map(mapToTreeNode),
                    documents: documents.filter(doc => (doc.folder_id || doc.folder) === folder.id),
                    expanded: true, // Default to expanded
                    totalFiles: folder.document_count || 0
                };
                return node;
            };

            // 1. Map all folders to tree nodes first (if they are nested in the response)
            // 2. Filter root folders that belong to this department
            const deptRootFolders = allFolders
                .filter(f => f.department_id === deptId)
                .map(mapToTreeNode);

            // 3. Find documents that don't belong to any folder
            const unassignedDocuments = documents.filter(
                doc => !doc.folder_id && !doc.folder
            );

            // 4. Create virtual node for unassigned documents if there are any
            if (unassignedDocuments.length > 0) {
                const unassignedNode: FolderTreeNode = {
                    id: `__unassigned_${deptId}`,
                    name: ' Tài liệu không có thư mục',
                    description: null,
                    parent_id: null,
                    department_id: deptId,
                    access_scope: 'department',
                    metadata: {},
                    created_by_id: null,
                    my_permission: 'none',
                    is_deleted: false,
                    deleted_at: null,
                    document_count: unassignedDocuments.length,
                    subfolder_count: 0,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    sub_folders: [],
                    subFolders: [],
                    documents: unassignedDocuments,
                    expanded: true,
                    totalFiles: unassignedDocuments.length
                };
                deptRootFolders.push(unassignedNode);
            }

            setFolders(deptRootFolders);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load folders');
        } finally {
            setLoading(false);
        }
    }, [deptId, enabled, canReadFolders, canReadDocuments]);

    const toggleFolder = useCallback((folderId: string) => {
        const toggleInTree = (nodes: FolderTreeNode[]): FolderTreeNode[] => {
            return nodes.map((node) => {
                if (node.id === folderId) {
                    return { ...node, expanded: !node.expanded };
                }
                if (node.subFolders.length > 0) {
                    return { ...node, subFolders: toggleInTree(node.subFolders) };
                }
                return node;
            });
        };

        setFolders((prev) => toggleInTree(prev));
    }, []);

    useEffect(() => {
        fetchFolders();
    }, [fetchFolders]);

    return {
        folders,
        loading,
        error,
        selectedFolder,
        selectedDocument,
        selectFolder: setSelectedFolder,
        selectDocument: setSelectedDocument,
        toggleFolder,
        refresh: fetchFolders,
    };
}
