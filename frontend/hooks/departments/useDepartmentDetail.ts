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

interface UseDepartmentHookOptions {
    enabled?: boolean;
    expand?: Array<'users' | 'folders' | 'documents'>;
}

export function useDepartmentDetail(
    deptId: string,
    options: UseDepartmentHookOptions = {}
): UseHookResult<DepartmentDetail> {
    const enabled = options.enabled ?? true;
    const [data, setData] = useState<DepartmentDetail | null>(null);
    const [loading, setLoading] = useState(enabled && !!deptId);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        if (!enabled || !deptId) {
            setLoading(false);
            return;
        }
        
        try {
            setLoading(true);
            setError(null);

            const expand = options.expand?.filter(Boolean) || [];
            const query = expand.length > 0 ? `?expand=${expand.join(',')}` : '';
            const response = await api.get<any>(`/departments/${deptId}/detail${query}`);

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
        if (!enabled || !deptId) {
            setData(null);
            setError(null);
            setLoading(false);
            return;
        }
        fetchData();
    }, [deptId, enabled, options.expand?.join(',')]);

    return { data, loading, error, refresh: fetchData };
}

/**
 * useDepartmentUsers - Fetch paginated users in department
 * API: GET /api/v1/departments/{id}/users?page=1&page_size=10
 */
export function useDepartmentUsers(
    deptId: string,
    page: number = 1,
    pageSize: number = 10,
    options: UseDepartmentHookOptions = {}
) {
    const enabled = options.enabled ?? true;
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(enabled && !!deptId);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!enabled || !deptId) {
            setData(null);
            setError(null);
            setLoading(false);
            return;
        }

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

        fetchData();
    }, [deptId, page, pageSize, enabled]);

    return { data, loading, error };
}

/**
 * useDepartmentFolders - Fetch paginated folders in department
 * API: GET /api/v1/departments/{id}/folders?page=1&page_size=10
 */
export function useDepartmentFolders(
    deptId: string,
    page: number = 1,
    pageSize: number = 10,
    options: UseDepartmentHookOptions = {}
) {
    const enabled = options.enabled ?? true;
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(enabled && !!deptId);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!enabled || !deptId) {
            setData(null);
            setError(null);
            setLoading(false);
            return;
        }

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

        fetchData();
    }, [deptId, page, pageSize, enabled]);

    return { data, loading, error };
}

/**
 * useDepartmentDocuments - Fetch paginated documents in department
 * API: GET /api/v1/departments/{id}/documents?page=1&page_size=10
 */
export function useDepartmentDocuments(
    deptId: string,
    page: number = 1,
    pageSize: number = 10,
    options: UseDepartmentHookOptions = {}
) {
    const enabled = options.enabled ?? true;
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(enabled && !!deptId);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!enabled || !deptId) {
            setData(null);
            setError(null);
            setLoading(false);
            return;
        }

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

        fetchData();
    }, [deptId, page, pageSize, enabled]);

    return { data, loading, error };
}
