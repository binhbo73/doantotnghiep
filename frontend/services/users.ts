/**
 * Users API Service
 * Handles user management API calls with proper error handling
 */

import { api } from '@/services/api'

/**
 * User data interface - matches backend response
 */
export interface User {
    id: string
    account_id: string
    username: string
    email: string
    first_name: string
    last_name: string
    full_name: string
    avatar_url: string | null
    address: string | null
    birthday: string | null
    department_name: string | null
    department_id?: string
    metadata: Record<string, unknown>
    status: 'active' | 'blocked' | 'inactive'
    is_active: boolean
    roles: Array<{
        id: string
        code: string
        name: string
        permissions: string[]
    }>
    permission_codes: string[]
    created_at: string
    updated_at: string
    date_joined: string
    last_login: string | null
}

/**
 * Paginated response interface
 */
export interface PaginatedResponse<T> {
    success: boolean
    data: T[]
    pagination: {
        total: number
        page: number
        page_size: number
        total_pages: number
    }
    message?: string
}

/**
 * Single user response interface
 */
export interface UserResponse {
    success: boolean
    data: User
    message?: string
}

/**
 * Create user payload
 */
export interface CreateUserPayload {
    username: string
    email: string
    first_name: string
    last_name: string
    department_id: string
    role_id: string
    password?: string
}

/**
 * Update user payload
 */
export interface UpdateUserPayload {
    email?: string
    first_name?: string
    last_name?: string
    department_id?: string
    role_id?: string
    is_active?: boolean
}

/**
 * Get all users with pagination and filters
 * GET /api/v1/users
 */
export async function getAllUsers(
    page: number = 1,
    pageSize: number = 10,
    search?: string,
    departmentId?: string,
    roleId?: string,
    isActive?: boolean
): Promise<PaginatedResponse<User>> {
    try {
        const params = new URLSearchParams({
            page: page.toString(),
            page_size: pageSize.toString(),
        })

        if (search) params.append('search', search)
        if (departmentId) params.append('department_id', departmentId)
        if (roleId) params.append('role_id', roleId)
        if (isActive !== undefined) params.append('is_active', isActive.toString())

        const response = await api.get<any>(
            `/users?${params.toString()}`
        )

        if (!response.success) {
            throw new Error(response.message || 'Failed to fetch users')
        }

        // Transform backend response to match frontend expectations
        // Backend returns: { success, data: { items, pagination }, message, ... }
        // Frontend expects: { success, data, pagination, ... }
        const items = response.data?.items || []
        const paginationData = response.data?.pagination || {}

        return {
            success: response.success,
            data: items,
            pagination: {
                total: paginationData.total_items || 0,
                page: paginationData.page || page,
                page_size: paginationData.page_size || pageSize,
                total_pages: paginationData.total_pages || 0,
            },
            message: response.message,
        }
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch users'
        console.error('❌ Error fetching users:', err)
        throw new Error(message)
    }
}

/**
 * Get single user by ID
 * GET /api/v1/users/{id}
 */
export async function getUserById(userId: string): Promise<User> {
    try {
        const response = await api.get<UserResponse>(`/users/${userId}`)

        if (!response.success) {
            throw new Error(response.message || 'Failed to fetch user')
        }

        return response.data
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch user'
        console.error('❌ Error fetching user:', err)
        throw new Error(message)
    }
}

/**
 * Create new user
 * POST /api/v1/users
 */
export async function createUser(payload: CreateUserPayload): Promise<User> {
    try {
        console.log('📤 Creating user:', payload.email)

        const response = await api.post<UserResponse>('/users', {
            username: payload.username,
            email: payload.email,
            first_name: payload.first_name,
            last_name: payload.last_name,
            department_id: payload.department_id,
            role_id: payload.role_id,
            password: payload.password,
        })

        if (!response.success) {
            throw new Error(response.message || 'Failed to create user')
        }

        console.log('✅ User created successfully:', response.data.id)
        return response.data
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create user'
        console.error('❌ Error creating user:', err)
        throw new Error(message)
    }
}

/**
 * Update user details
 * PUT /api/v1/users/{id}
 */
export async function updateUser(userId: string, payload: UpdateUserPayload): Promise<User> {
    try {
        console.log('📤 Updating user:', userId)

        const response = await api.put<UserResponse>(`/users/${userId}`, payload)

        if (!response.success) {
            throw new Error(response.message || 'Failed to update user')
        }

        console.log('✅ User updated successfully')
        return response.data
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update user'
        console.error('❌ Error updating user:', err)
        throw new Error(message)
    }
}

/**
 * Delete user
 * DELETE /api/v1/users/{id}
 */
export async function deleteUser(userId: string): Promise<void> {
    try {
        console.log('📤 Deleting user:', userId)

        const response = await api.delete<{ success: boolean; message?: string }>(
            `/users/${userId}`
        )

        if (!response.success) {
            throw new Error(response.message || 'Failed to delete user')
        }

        console.log('✅ User deleted successfully')
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to delete user'
        console.error('❌ Error deleting user:', err)
        throw new Error(message)
    }
}

/**
 * Bulk update user status
 * PATCH /api/v1/users/bulk/status
 */
export async function updateUsersStatus(
    userIds: string[],
    isActive: boolean
): Promise<{ updated_count: number }> {
    try {
        const response = await api.patch<{ success: boolean; data: { updated_count: number } }>(
            '/users/bulk/status',
            {
                user_ids: userIds,
                is_active: isActive,
            }
        )

        if (!response.success) {
            throw new Error(response.message || 'Failed to update user status')
        }

        return response.data
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update user status'
        console.error('❌ Error updating user status:', err)
        throw new Error(message)
    }
}

/**
 * Reset user password
 * POST /api/v1/users/{id}/reset-password
 */
export async function resetUserPassword(userId: string): Promise<{ temporary_password: string }> {
    try {
        const response = await api.post<{
            success: boolean
            data: { temporary_password: string }
        }>(`/users/${userId}/reset-password`, {})

        if (!response.success) {
            throw new Error(response.message || 'Failed to reset password')
        }

        return response.data
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to reset password'
        console.error('❌ Error resetting password:', err)
        throw new Error(message)
    }
}
