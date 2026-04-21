/**
 * Custom Hooks for Department APIs
 * Handles API calls to Hybrid Approach endpoints
 */

import { useEffect, useState } from 'react';
import { DepartmentDetail, PaginatedResponse, UserDetail, FolderDetail, DocumentDetail } from '@/types/departments';
import { api } from '@/services/api/client';

interface UseHookResult<T> {
    data: T | null;
    loading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
}

export function useDepartmentDetail(deptId: string): UseHookResult<DepartmentDetail> {
    const [data, setData] = useState<DepartmentDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        if (!deptId) return;
        
        try {
            setLoading(true);
            setError(null);

            // Use Expanded View API to get department info + first page of users/folders/docs
            const response = await api.get<any>(`/departments/${deptId}/detail?expand=users,folders,documents`);

            if (response.success) {
                setData(response.data);
            } else {
                setError(response.message || 'Lỗi tải dữ liệu phòng ban');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Lỗi không xác định');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [deptId]);

    return { data, loading, error, refresh: fetchData };
}

/**
 * useDepartmentUsers - Fetch paginated users in department
 * API: GET /api/v1/departments/{id}/users?page=1&page_size=10
 */
export function useDepartmentUsers(
    deptId: string,
    page: number = 1,
    pageSize: number = 10
) {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                setError(null);

                const response = await api.get<any>(
                    `/departments/${deptId}/users?page=${page}&page_size=${pageSize}`
                );

                if (response.success) {
                    setData(response.data);
                } else {
                    setError(response.message || 'Lỗi tải danh sách nhân sự');
                }
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Lỗi không xác định');
            } finally {
                setLoading(false);
            }
        };

        if (deptId) {
            fetchData();
        }
    }, [deptId, page, pageSize]);

    return { data, loading, error };
}

/**
 * useDepartmentFolders - Fetch paginated folders in department
 * API: GET /api/v1/departments/{id}/folders?page=1&page_size=10
 */
export function useDepartmentFolders(
    deptId: string,
    page: number = 1,
    pageSize: number = 10
) {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                setError(null);

                const response = await api.get<any>(
                    `/departments/${deptId}/folders?page=${page}&page_size=${pageSize}`
                );

                if (response.success) {
                    setData(response.data);
                } else {
                    setError(response.message || 'Lỗi tải danh sách thư mục');
                }
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Lỗi không xác định');
            } finally {
                setLoading(false);
            }
        };

        if (deptId) {
            fetchData();
        }
    }, [deptId, page, pageSize]);

    return { data, loading, error };
}

/**
 * useDepartmentDocuments - Fetch paginated documents in department
 * API: GET /api/v1/departments/{id}/documents?page=1&page_size=10
 */
export function useDepartmentDocuments(
    deptId: string,
    page: number = 1,
    pageSize: number = 10
) {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                setError(null);

                const response = await api.get<any>(
                    `/departments/${deptId}/documents?page=${page}&page_size=${pageSize}`
                );

                if (response.success) {
                    setData(response.data);
                } else {
                    setError(response.message || 'Lỗi tải danh sách tài liệu');
                }
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Lỗi không xác định');
            } finally {
                setLoading(false);
            }
        };

        if (deptId) {
            fetchData();
        }
    }, [deptId, page, pageSize]);

    return { data, loading, error };
}
