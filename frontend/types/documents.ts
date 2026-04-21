/**
 * Document Data Types
 */

export interface DocumentDetail {
    id: string;
    filename: string;
    file_type: string;
    file_size: number;
    status: 'DRAFT' | 'ACTIVE' | 'ARCHIVED' | 'DELETED';
    description?: string;
    folder_id?: string;
    department_id?: string;
    file_url?: string;
    created_at: string;
    updated_at: string;
}

export interface DocumentNode {
    id: string;
    filename: string;
    file_type: string;
    file_size: number;
    status: 'DRAFT' | 'ACTIVE' | 'ARCHIVED' | 'DELETED';
}
