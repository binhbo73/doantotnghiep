/**
 * Folder Data Types
 */

export interface FolderDetail {
    id: string;
    name: string;
    description?: string;
    access_scope: 'PUBLIC' | 'PRIVATE';
    parent_id?: string;
    department_id?: string;
    document_count: number;
    subfolder_count: number;
    created_at: string;
    updated_at: string;
}

export interface FolderNode {
    id: string;
    name: string;
    access_scope: 'PUBLIC' | 'PRIVATE';
    document_count: number;
    subfolder_count: number;
}
