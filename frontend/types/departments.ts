/**
 * Department Data Types
 */

export interface UserDetail {
    id: string;
    username: string;
    email: string;
    full_name: string;
    avatar_url?: string;
}

export interface DepartmentNode {
    id: string;
    name: string;
    member_count: number;
    folder_count: number;
    document_count: number;
    sub_departments: DepartmentNode[];
}

export interface DepartmentDetail {
    id: string;
    name: string;
    description?: string;
    manager: UserDetail | null;
    member_count: number;
    folder_count: number;
    document_count: number;
    sub_department_count: number;
    sub_departments: DepartmentNode[];
    created_at: string;
    updated_at: string;

    // Expanded data
    users?: PaginatedResponse<UserDetail>;
    folders?: PaginatedResponse<FolderDetail>;
    documents?: PaginatedResponse<DocumentDetail>;
}

export interface FolderDetail {
    id: string;
    name: string;
    access_scope: 'PUBLIC' | 'PRIVATE';
    document_count: number;
    subfolder_count: number;
}

export interface DocumentDetail {
    id: string;
    filename: string;
    file_type: string;
    file_size: number;
    status: 'DRAFT' | 'ACTIVE' | 'ARCHIVED' | 'DELETED';
    folder_id?: string;
    department_id?: string;
    created_at: string;
    updated_at: string;
}

export interface PaginationData {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
}

export interface PaginatedResponse<T> {
    items: T[];
    pagination: PaginationData;
}
