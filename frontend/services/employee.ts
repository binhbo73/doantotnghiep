/**
 * Employee API Service
 * Handles employee-related API calls with proper headers and error handling
 */

import { api } from '@/services/api'

export interface CreateEmployeePayload {
    username: string
    email: string
    first_name: string
    last_name: string
    department_id: string
    role_id: string
}

export interface EmployeeResponse {
    id: string
    username: string
    email: string
    first_name: string
    last_name: string
    department_id: string
    role_id: string
    created_at: string
    updated_at: string
}

/**
 * Create a new employee
 * POST /api/v1/accounts/create
 */
export async function createEmployee(payload: CreateEmployeePayload): Promise<EmployeeResponse> {
    try {
        console.log('📤 Creating employee:', payload.email)

        // Use the correct accounts/create endpoint
        const response = await api.post<{
            success: boolean
            data: EmployeeResponse
            message: string
        }>('/accounts/create', {
            username: payload.username,
            email: payload.email,
            first_name: payload.first_name,
            last_name: payload.last_name,
            department_id: payload.department_id,
            role_id: payload.role_id,
        })

        if (!response.success) {
            throw new Error(response.message || 'Failed to create employee')
        }

        console.log('✅ Employee created successfully:', response.data.id)
        return response.data
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create employee'
        console.error('❌ Error creating employee:', err)
        throw new Error(message)
    }
}

/**
 * Get employee details
 * GET /api/v1/users/{id}
 */
export async function getEmployee(employeeId: string): Promise<EmployeeResponse> {
    try {
        const response = await api.get<{
            success: boolean
            data: EmployeeResponse
            message: string
        }>(`/users/${employeeId}`)

        if (!response.success) {
            throw new Error(response.message || 'Failed to fetch employee')
        }

        return response.data
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch employee'
        console.error('❌ Error fetching employee:', err)
        throw new Error(message)
    }
}

/**
 * Update employee details
 * PUT /api/v1/users/{id}
 */
export async function updateEmployee(
    employeeId: string,
    payload: Partial<CreateEmployeePayload>
): Promise<EmployeeResponse> {
    try {
        console.log('📤 Updating employee:', employeeId)

        const response = await api.put<{
            success: boolean
            data: EmployeeResponse
            message: string
        }>(`/users/${employeeId}`, payload)

        if (!response.success) {
            throw new Error(response.message || 'Failed to update employee')
        }

        console.log('✅ Employee updated successfully')
        return response.data
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update employee'
        console.error('❌ Error updating employee:', err)
        throw new Error(message)
    }
}
