// services/audit.ts - API service for audit logs
import { api, ApiError } from './api'

export interface ActivityItem {
    id: string
    title: string
    description: string
    time: string
    avatarChar: string
    avatarBgColor?: string
    category?: string
}

export interface AuditLogResponse {
    id: string
    account_id?: string
    account_username?: string
    action: string
    action_display: string
    activity_summary?: string
    resource_id?: string
    resource_type?: string
    resource_label?: string
    status?: 'success' | 'failed' | 'denied' | 'pending' | string
    http_method?: string
    path?: string
    status_code?: number
    metadata?: Record<string, unknown>
    query_text?: string
    ip_address?: string
    created_at: string
    updated_at?: string
}

export interface AuditLogDetailResponse {
    id: string
    account?: {
        id: string
        username: string
        email: string
        first_name: string
        last_name: string
    }
    action: string
    action_display: string
    activity_summary?: string
    resource_id?: string
    resource_type?: string
    resource_label?: string
    status?: 'success' | 'failed' | 'denied' | 'pending' | string
    http_method?: string
    path?: string
    status_code?: number
    metadata?: Record<string, unknown>
    query_text?: string
    ip_address?: string
    user_agent?: string
    created_at: string
    updated_at?: string
}

export interface RecentActivityResponse {
    items: ActivityItem[]
    count: number
}

export interface AuditStatisticsResponse {
    total_logs: number
    logs_today: number
    logs_this_week: number
    logs_this_month: number
    most_active_user?: string
    most_common_action?: string
    actions_breakdown: Record<string, number>
    status_breakdown?: Record<string, number>
    users_breakdown: Record<string, number>
}

function getActionColor(action: string): string {
    const actionColors: Record<string, string> = {
        LOGIN: '#0058be',
        LOGOUT: '#727785',
        CREATE: '#52c41a',
        UPLOAD: '#faad14',
        DELETE: '#f5222d',
        QUERY: '#1890ff',
        EDIT: '#eb2f96',
        UPDATE: '#722ed1',
        DOWNLOAD: '#13c2c2',
        SHARE: '#fa541c',
        IMPORT: '#1890ff',
        DELETE_USER: '#f5222d',
        CHANGE_ROLE: '#eb2f96',
        CREATE_ROLE: '#52c41a',
        FEEDBACK: '#faad14',
        GRANT_ACL: '#52c41a',
        REVOKE_ACL: '#f5222d',
        MUTATION: '#1890ff',
    }

    return actionColors[action] || '#0058be'
}

function getRelativeTime(isoDate?: string): string {
    if (!isoDate) return 'Vừa xong'

    const createdAt = new Date(isoDate)
    if (Number.isNaN(createdAt.getTime())) return 'Vừa xong'

    const diffMs = Date.now() - createdAt.getTime()
    const diffMinutes = Math.max(1, Math.floor(diffMs / 60000))
    if (diffMinutes < 60) return `${diffMinutes} phút trước`

    const diffHours = Math.floor(diffMinutes / 60)
    if (diffHours < 24) return `${diffHours} giờ trước`

    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays} ngày trước`
}

function buildActivityItem(log: AuditLogResponse): ActivityItem {
    const username = log.account_username || 'Hệ thống'
    const action = log.action?.toUpperCase() || 'UNKNOWN'
    const resourceName = 'tài nguyên'

    const titleMap: Record<string, string> = {
        LOGIN: `${username} đã đăng nhập`,
        LOGOUT: `${username} đã đăng xuất`,
        CREATE: `${username} đã tạo ${resourceName}`,
        UPLOAD: `${username} đã tải lên ${resourceName}`,
        DELETE: `${username} đã xóa ${resourceName}`,
        QUERY: `${username} đã truy vấn dữ liệu`,
        EDIT: `${username} đã chỉnh sửa ${resourceName}`,
        UPDATE: `${username} đã cập nhật ${resourceName}`,
        DOWNLOAD: `${username} đã tải xuống ${resourceName}`,
        SHARE: `${username} đã chia sẻ ${resourceName}`,
        IMPORT: `${username} đã nhập dữ liệu`,
        DELETE_USER: `${username} đã xóa người dùng`,
        CHANGE_ROLE: `${username} đã thay đổi vai trò`,
        CREATE_ROLE: `${username} đã tạo vai trò mới`,
        FEEDBACK: `${username} đã gửi phản hồi`,
        GRANT_ACL: `${username} đã cấp quyền truy cập`,
        REVOKE_ACL: `${username} đã thu hồi quyền truy cập`,
        MUTATION: `${username} đã thực hiện thay đổi dữ liệu`,
    }

    const descriptionMap: Record<string, string> = {
        LOGIN: 'Được chia sẻ bởi Team Marketing',
        LOGOUT: 'Phiên làm việc kết thúc',
        UPLOAD: log.resource_id ? `ID tài nguyên: ${log.resource_id}` : 'Không có mô tả',
        CREATE: log.resource_id ? `ID tài nguyên: ${log.resource_id}` : 'Không có mô tả',
        DELETE: log.resource_id ? `ID tài nguyên: ${log.resource_id}` : 'Không có mô tả',
    }

    return {
        id: log.id,
        title: titleMap[action] || `${username} thực hiện ${action}`,
        description: log.query_text || descriptionMap[action] || (log.ip_address ? `Địa chỉ IP: ${log.ip_address}` : 'Không có mô tả'),
        time: getRelativeTime(log.created_at),
        avatarChar: username?.[0]?.toUpperCase() || '?',
        avatarBgColor: getActionColor(action),
        category: log.action_display || action,
    }
}

/**
 * Get list of audit logs with filtering
 */
export async function getAuditLogs(params?: {
    action?: string
    status?: string
    account_id?: string
    username?: string
    resource_id?: string
    resource_type?: string
    http_method?: string
    status_code?: string
    start_date?: string
    end_date?: string
    search?: string
    page?: number
    page_size?: number
}): Promise<{
    success: boolean
    data: {
        items: AuditLogResponse[]
        pagination: {
            page: number
            page_size: number
            total_items: number
            total_pages: number
        }
    }
    message: string
}> {
    const queryParams = new URLSearchParams()
    if (params?.action) queryParams.append('action', params.action)
    if (params?.status) queryParams.append('status', params.status)
    if (params?.account_id) queryParams.append('account_id', params.account_id)
    if (params?.username) queryParams.append('username', params.username)
    if (params?.resource_id) queryParams.append('resource_id', params.resource_id)
    if (params?.resource_type) queryParams.append('resource_type', params.resource_type)
    if (params?.http_method) queryParams.append('http_method', params.http_method)
    if (params?.status_code) queryParams.append('status_code', params.status_code)
    if (params?.start_date) queryParams.append('start_date', params.start_date)
    if (params?.end_date) queryParams.append('end_date', params.end_date)
    if (params?.search) queryParams.append('search', params.search)
    queryParams.append('page', String(params?.page || 1))
    queryParams.append('page_size', String(params?.page_size || 20))

    return api.get(`/audit-logs?${queryParams.toString()}`)
}

/**
 * Get detailed audit log by ID
 */
export async function getAuditLogDetail(auditLogId: string): Promise<{
    success: boolean
    data: AuditLogDetailResponse
    message: string
}> {
    return api.get(`/audit-logs/${auditLogId}`)
}

/**
 * Get recent activities for dashboard
 * Used by "Hoạt động gần đây" component
 */
export async function getRecentActivities(params?: {
    limit?: number
    user_id?: string
}): Promise<{
    success: boolean
    data: RecentActivityResponse
    message: string
}> {
    const queryParams = new URLSearchParams()
    if (params?.limit) queryParams.append('limit', String(params.limit))
    if (params?.user_id) queryParams.append('user_id', params.user_id)

    try {
        return await api.get(`/audit-logs/recent-activity?${queryParams.toString()}`)
    } catch (error) {
        if (error instanceof ApiError && error.statusCode === 404) {
            const listResponse = await getAuditLogs({
                page: 1,
                page_size: params?.limit || 10,
                account_id: params?.user_id,
            })

            return {
                success: true,
                data: {
                    items: listResponse.data.items.map(buildActivityItem),
                    count: listResponse.data.items.length,
                },
                message: listResponse.message,
            }
        }

        throw error
    }
}

/**
 * Get audit log statistics
 */
export async function getAuditStatistics(): Promise<{
    success: boolean
    data: AuditStatisticsResponse
    message: string
}> {
    return api.get('/audit-logs/statistics')
}

/**
 * Export audit logs as CSV or JSON
 */
export async function exportAuditLogs(params?: {
    format?: 'csv' | 'json'
    action?: string
    status?: string
    resource_type?: string
    start_date?: string
    end_date?: string
}): Promise<{
    success: boolean
    data: AuditLogDetailResponse[] | string
    message: string
}> {
    const queryParams = new URLSearchParams()
    queryParams.append('format', params?.format || 'csv')
    if (params?.action) queryParams.append('action', params.action)
    if (params?.status) queryParams.append('status', params.status)
    if (params?.resource_type) queryParams.append('resource_type', params.resource_type)
    if (params?.start_date) queryParams.append('start_date', params.start_date)
    if (params?.end_date) queryParams.append('end_date', params.end_date)

    return api.get(`/audit-logs/export?${queryParams.toString()}`)
}
