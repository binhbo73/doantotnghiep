import { api } from './api'
import { Department, ApiResponseWithPagination } from '@/types/api'

export interface DepartmentQueryParams {
    page?: number
    page_size?: number
    search?: string
}

export async function fetchDepartments(params?: DepartmentQueryParams): Promise<ApiResponseWithPagination<Department>> {
    try {
        const page = params?.page || 1
        const page_size = params?.page_size || 20
        const search = params?.search

        const queryParts: string[] = []
        queryParts.push(`page=${page}`)
        queryParts.push(`page_size=${page_size}`)
        if (search) {
            queryParts.push(`search=${encodeURIComponent(search)}`)
        }
        const queryString = queryParts.join('&')

        const response = await api.get<ApiResponseWithPagination<Department>>(
            `/departments?${queryString}`
        )

        if (!response.success) {
            throw new Error(response.message || 'Failed to fetch departments')
        }

        return response
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch departments'
        console.error('❌ Error fetching departments:', err)
        throw new Error(message)
    }
}

export async function createDepartment(data: {
    name: string
    description?: string
    parent_id?: string | null
    manager_id?: string | null
}) {
    const response = await api.post<Department>(
        '/departments',
        data
    )
    return response
}

export async function updateDepartment(
    id: string,
    data: Partial<{
        name: string
        description: string
        parent_id: string | null
        manager_id: string | null
    }>
) {
    const response = await api.put<Department>(
        `/departments/${id}`,
        data
    )
    return response
}

export async function deleteDepartment(id: string) {
    await api.delete(`/departments/${id}`)
}
