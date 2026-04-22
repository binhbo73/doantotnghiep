/**
 * Hook for Department Folders & Documents API
 * Fetches folders and documents for a department in tree structure
 */

import { useEffect, useState, useCallback } from 'react';
import { FolderDetail } from '@/types/folders';
import { api } from '@/services/api/client';

export interface DocumentNode {
    id: string;
    filename: string;
    original_name: string;
    file_type: string;
    file_size: number;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    created_at: string;
    updated_at: string;
    access_scope: 'PUBLIC' | 'PRIVATE';
    uploader?: any;
}

export interface FolderTreeNode extends FolderDetail {
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

export function useDepartmentFolders(deptId: string): UseDepartmentFoldersResult {
    const [folders, setFolders] = useState<FolderTreeNode[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedFolder, setSelectedFolder] = useState<FolderTreeNode | null>(null);
    const [selectedDocument, setSelectedDocument] = useState<DocumentNode | null>(null);

    const fetchFolders = useCallback(async () => {
        if (!deptId) return;

        try {
            setLoading(true);
            setError(null);

            // Fetch folders for department - API base already includes /api/v1
            const foldersResponse = await api.get<any>(
                `/departments/${deptId}/folders?page=1&page_size=1000`
            );

            // Fetch documents for department
            const docsResponse = await api.get<any>(
                `/departments/${deptId}/documents?page=1&page_size=1000`
            );

            if (foldersResponse.success && foldersResponse.data?.items) {
                const folderMap = new Map<string, FolderTreeNode>();
                const rootFolders: FolderTreeNode[] = [];
                const documents: DocumentNode[] = docsResponse.data?.items || [];

                // First pass: create all folder nodes
                foldersResponse.data.items.forEach((folder: any) => {
                    const treeNode: FolderTreeNode = {
                        ...folder,
                        subFolders: [],
                        documents: [],
                        expanded: false,
                        totalFiles: folder.document_count || 0,
                    };
                    folderMap.set(folder.id, treeNode);
                });

                // Assign documents to folders
                documents.forEach((doc: DocumentNode) => {
                    if (doc.folder_id) {
                        const folder = folderMap.get(doc.folder_id);
                        if (folder) {
                            folder.documents.push(doc);
                        }
                    }
                });

                // Second pass: build hierarchy
                folderMap.forEach((folder) => {
                    if (folder.parent_id) {
                        const parent = folderMap.get(folder.parent_id);
                        if (parent) {
                            parent.subFolders.push(folder);
                        }
                    } else {
                        rootFolders.push(folder);
                    }
                });

                setFolders(rootFolders);
            } else {
                setError(foldersResponse.message || 'Failed to load folders');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load folders');
        } finally {
            setLoading(false);
        }
    }, [deptId]);

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
