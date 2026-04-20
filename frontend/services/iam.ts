/**
 * IAM Service - Role & Permission Management
 * Handles all calls to the IAM API endpoints
 */

import { api } from './api'
import { IamRole, IamPermission, ApiResponseWithPagination } from '@/types/api'

export interface RolesQueryParams {
    page?: number
    page_size?: number
    search?: string
}

export interface PermissionsQueryParams {
    page?: number
    page_size?: number
    search?: string
}

// ============================================
// ROLES
// ============================================

export async function fetchRoles(params?: RolesQueryParams): Promise<ApiResponseWithPagination<IamRole>> {
    try {
        const page = params?.page || 1
        const page_size = params?.page_size || 100
        const search = params?.search

        // Build query string
        const queryParts: string[] = []
        queryParts.push(`page=${page}`)
        queryParts.push(`page_size=${page_size}`)
        if (search) {
            queryParts.push(`search=${encodeURIComponent(search)}`)
        }
        const queryString = queryParts.join('&')

        // Call API
        const response = await api.get<ApiResponseWithPagination<IamRole>>(
            `/iam/roles?${queryString}`
        )

        if (!response.success) {
            throw new Error(response.message || 'Failed to fetch roles')
        }

        return response
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch roles'
        console.error('❌ Error fetching roles:', err)
        throw new Error(message)
    }
}

export async function fetchRoleDetail(roleId: string) {
    const response = await api.get<IamRole>(
        `/iam/roles/${roleId}`
    )
    return response.data
}

export async function createRole(data: {
    code: string
    name: string
    description?: string
    permission_ids?: string[]
}) {
    const response = await api.post<IamRole>(
        '/iam/roles',
        data
    )
    return response.data
}

export async function updateRole(
    roleId: string,
    data: {
        name?: string
        description?: string
        permission_ids?: string[]
    }
) {
    const response = await api.put<IamRole>(
        `/iam/roles/${roleId}`,
        data
    )
    return response.data
}

export async function deleteRole(roleId: string) {
    await api.delete(`/iam/roles/${roleId}`)
}

export async function assignPermissionsToRole(
    roleId: string,
    permissionIds: string[]
) {
    const response = await api.post<IamRole>(
        `/iam/roles/${roleId}/permissions`,
        { permission_ids: permissionIds }
    )
    return response.data
}

export async function removePermissionsFromRole(
    roleId: string,
    permissionIds: string[]
) {
    // Note: This endpoint might need to be POST or PATCH instead of DELETE
    // Check with backend API documentation
    const response = await api.post(
        `/iam/roles/${roleId}/permissions/remove`,
        { permission_ids: permissionIds }
    )
    return response
}

// ============================================
// PERMISSIONS
// ============================================

export async function fetchPermissions(params?: PermissionsQueryParams): Promise<ApiResponseWithPagination<IamPermission>> {
    try {
        const page = params?.page || 1
        const page_size = params?.page_size || 20
        const search = params?.search

        // Build query string
        const queryParts: string[] = []
        queryParts.push(`page=${page}`)
        queryParts.push(`page_size=${page_size}`)
        if (search) {
            queryParts.push(`search=${encodeURIComponent(search)}`)
        }
        const queryString = queryParts.join('&')

        // Call API
        const response = await api.get<ApiResponseWithPagination<IamPermission>>(
            `/iam/permissions?${queryString}`
        )

        if (!response.success) {
            throw new Error(response.message || 'Failed to fetch permissions')
        }

        return response
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch permissions'
        console.error('❌ Error fetching permissions:', err)
        throw new Error(message)
    }
}

export async function fetchPermissionDetail(permissionId: string) {
    const response = await api.get<IamPermission>(
        `/iam/permissions/${permissionId}`
    )
    return response.data
}

export async function createPermission(data: {
    code: string
    resource: string
    action: string
    description?: string
}) {
    const response = await api.post<IamPermission>(
        '/iam/permissions',
        data
    )
    return response.data
}

export async function updatePermission(
    permissionId: string,
    data: {
        description?: string
    }
) {
    const response = await api.put<IamPermission>(
        `/iam/permissions/${permissionId}`,
        data
    )
    return response.data
}

export async function deletePermission(permissionId: string) {
    await api.delete(`/iam/permissions/${permissionId}`)
}
