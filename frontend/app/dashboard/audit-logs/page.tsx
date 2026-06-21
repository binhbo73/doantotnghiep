'use client'

import React, { useCallback, useEffect, useState } from 'react'
import { AccessDeniedPage } from '@/components/common/AccessDeniedPage'
import { AppIcon } from '@/components/ui/AppIcon'
import { useRBAC } from '@/hooks/useRBAC'
import { AuditLogResponse, getAuditLogs } from '@/services/audit'
import { getAllUsers, User } from '@/services/users'

const PAGE_SIZE = 25

const STATUS_STYLE: Record<string, string> = {
    success: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
    failed: 'bg-red-50 text-red-700 ring-red-100',
    denied: 'bg-amber-50 text-amber-700 ring-amber-100',
    pending: 'bg-blue-50 text-blue-700 ring-blue-100',
}

const STATUS_LABELS: Record<string, string> = {
    success: 'Thành công',
    failed: 'Lỗi',
    denied: 'Bị chặn',
    pending: 'Đang xử lý',
}

const ACTION_LABELS: Record<string, string> = {
    READ: 'Xem',
    CREATE: 'Tạo mới',
    UPDATE: 'Cập nhật',
    DELETE: 'Xóa',
    UPLOAD: 'Tải lên',
    DOWNLOAD: 'Tải xuống',
    MOVE: 'Di chuyển',
    RESTORE: 'Khôi phục',
    GRANT_PERMISSION: 'Cấp quyền',
    REVOKE_PERMISSION: 'Thu hồi quyền',
    CHAT_MESSAGE: 'Chat',
    FEEDBACK: 'Phản hồi',
    ACCESS_DENIED: 'Bị chặn quyền',
    ERROR: 'Lỗi hệ thống',
    LOGIN: 'Đăng nhập',
    LOGOUT: 'Đăng xuất',
}

const VI_STATUS_LABELS: Record<string, string> = {
    success: 'Thành công',
    failed: 'Lỗi',
    denied: 'Bị chặn',
    pending: 'Đang xử lý',
}

const VI_ACTION_LABELS: Record<string, string> = {
    READ: 'Xem',
    CREATE: 'Tạo mới',
    UPDATE: 'Cập nhật',
    DELETE: 'Xóa',
    UPLOAD: 'Tải lên',
    DOWNLOAD: 'Tải xuống',
    MOVE: 'Di chuyển',
    RESTORE: 'Khôi phục',
    GRANT_PERMISSION: 'Cấp quyền',
    REVOKE_PERMISSION: 'Thu hồi quyền',
    UPDATE_PERMISSION: 'Cập nhật quyền',
    CHAT_MESSAGE: 'Chat',
    FEEDBACK: 'Phản hồi',
    ACCESS_DENIED: 'Bị chặn quyền',
    ERROR: 'Lỗi hệ thống',
    LOGIN: 'Đăng nhập',
    LOGOUT: 'Đăng xuất',
}

function formatDateTime(value?: string | null) {
    if (!value) return 'Không xác định'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString('vi-VN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    })
}

function getActor(log: AuditLogResponse) {
    return log.account_username || 'Hệ thống / Không xác định'
}

function getStatusLabel(status?: string) {
    if (!status) return 'Không rõ'
    return STATUS_LABELS[status] || status
}

function getActionLabel(action: string) {
    return ACTION_LABELS[action] || action
}

function getActorLabel(log: AuditLogResponse) {
    if (log.account_username) return getActor(log)
    return log.account_username || 'Hệ thống / Không xác định'
}

function getStatusText(status?: string) {
    if (!status) return 'Không rõ'
    return VI_STATUS_LABELS[status] || getStatusLabel(status)
}

function getActionText(action: string) {
    const extraLabels: Record<string, string> = {
        UPDATE_USER_PROFILE: 'Cập nhật hồ sơ người dùng',
        UPDATE_OWN_PROFILE: 'Cập nhật hồ sơ cá nhân',
        UPLOAD_AVATAR: 'Cập nhật ảnh đại diện',
        UPDATE_ACCOUNT: 'Cập nhật tài khoản',
        CHANGE_USER_STATUS: 'Thay đổi trạng thái người dùng',
        CHANGE_ACCOUNT_DEPARTMENT: 'Thay đổi phòng ban của người dùng',
        ADMIN_RESET_PASSWORD: 'Đặt lại mật khẩu cho người dùng',
        RESET_PASSWORD: 'Đặt lại mật khẩu',
        CHANGE_PASSWORD: 'Đổi mật khẩu',
        CREATE_ROLE: 'Tạo vai trò',
        UPDATE_ROLE: 'Cập nhật vai trò',
        DELETE_ROLE: 'Xóa vai trò',
        CREATE_PERMISSION: 'Tạo quyền hạn',
        UPDATE_PERMISSION: 'Cập nhật quyền hạn',
        DELETE_PERMISSION: 'Xóa quyền hạn',
        ASSIGN_PERMISSION: 'Gán quyền',
        REMOVE_PERMISSION: 'Gỡ quyền',
    }
    Object.assign(extraLabels, {
        CREATE_FOLDER: 'Tạo thư mục',
        UPDATE_FOLDER: 'Cập nhật thư mục',
        DELETE_FOLDER: 'Xóa thư mục',
        MOVE_FOLDER: 'Di chuyển thư mục',
        CREATE_DEPARTMENT: 'Tạo phòng ban',
        UPDATE_DEPARTMENT: 'Cập nhật phòng ban',
        DELETE_DEPARTMENT: 'Xóa phòng ban',
        DOCUMENT_UPLOAD: 'Tải lên tài liệu',
        DOCUMENT_DOWNLOAD: 'Tải xuống tài liệu',
    })
    return extraLabels[action] || VI_ACTION_LABELS[action] || getActionLabel(action)
}

function asRecord(value: unknown): Record<string, unknown> {
    return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function getString(value: unknown) {
    return typeof value === 'string' ? value : ''
}

function getStringArray(value: unknown) {
    return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && item.length > 0) : []
}

function getBodySummary(log: AuditLogResponse) {
    return asRecord(asRecord(log.metadata).body_summary)
}

function getChatQuestion(log: AuditLogResponse) {
    const metadata = asRecord(log.metadata)
    const bodySummary = getBodySummary(log)
    return (
        getString(bodySummary.chat_question) ||
        getString(metadata.chat_question) ||
        getString(metadata.latest_question)
    )
}

function getNumber(value: unknown) {
    return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

function normalizeAuditText(value: string) {
    const labels: Record<string, string> = {
        'Xem tong quan/chi tiet phong ban': 'Xem tổng quan phòng ban',
        'Xem nhan su trong phong ban': 'Xem nhân sự trong phòng ban',
        'Xem kho thu muc cua phong ban': 'Xem kho thư mục của phòng ban',
        'Xem tai lieu trong phong ban': 'Xem tài liệu trong phòng ban',
        'Xem chi tiet phong ban': 'Xem chi tiết phòng ban',
        'Xem tai lieu trong thu muc': 'Xem tài liệu trong thư mục',
        'Xem quyen truy cap thu muc': 'Xem quyền truy cập thư mục',
        'Di chuyen thu muc': 'Di chuyển thư mục',
        'Xem chi tiet thu muc': 'Xem chi tiết thư mục',
        'Tai xuong tai lieu': 'Tải xuống tài liệu',
        'Xem truoc tai lieu': 'Xem trước tài liệu',
        'Xem quyen truy cap tai lieu': 'Xem quyền truy cập tài liệu',
        'Xem phien ban tai lieu': 'Xem phiên bản tài liệu',
        'Xem anh/bang bieu trich xuat tu tai lieu': 'Xem ảnh/bảng biểu trích xuất từ tài liệu',
        'Di chuyen tai lieu': 'Di chuyển tài liệu',
        'Xem trang thai xu ly tai lieu': 'Xem trạng thái xử lý tài liệu',
        'Lap chi muc lai tai lieu': 'Lập chỉ mục lại tài liệu',
        'Xem lich su tin nhan cua cuoc chat': 'Xem lịch sử tin nhắn của cuộc chat',
        'Xem tai lieu/thu muc dinh kem cuoc chat': 'Xem tài liệu/thư mục đính kèm cuộc chat',
        'Gui cau hoi chat': 'Gửi câu hỏi chat',
        'Xem cuoc chat': 'Xem cuộc chat',
    }
    return labels[value] || value
}

function cleanResourceLabel(value: string) {
    return value
        .replace(/\s*\([^)]*\)\s*$/g, '')
        .replace(/^Phong ban:/, 'Phòng ban:')
        .replace(/^Thu muc:/, 'Thư mục:')
        .replace(/^Tai lieu:/, 'Tài liệu:')
        .replace(/^Cuoc chat:/, 'Cuộc chat:')
        .replace(/^Nguoi dung:/, 'Người dùng:')
        .trim()
}

function hasTechnicalId(value: string) {
    return (
        /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i.test(value) ||
        /:\s*[0-9a-f]{7,}\b/i.test(value)
    )
}

function isSystemFallbackLabel(value: string) {
    const normalized = value.toLowerCase()
    return (
        !value ||
        hasTechnicalId(value) ||
        normalized.includes('dữ liệu hệ thống') ||
        normalized.includes('dá»¯ liá»‡u') ||
        normalized.includes('du lieu he thong')
    )
}

function getActionFallbackTitle(log: AuditLogResponse) {
    const action = getActionText(log.action)
    if (log.resource_type === 'users' || log.resource_type === 'accounts') return `${action} người dùng`
    if (log.resource_type === 'departments') return `${action} phòng ban`
    if (log.resource_type === 'folders') return `${action} thư mục`
    if (log.resource_type === 'documents') return `${action} tài liệu`
    if (log.resource_type === 'roles' || log.resource_type === 'iam_roles') return `${action} vai trò`
    if (log.resource_type === 'permissions' || log.resource_type === 'iam_permissions' || log.resource_type === 'Permission') return `${action} quyền hạn`
    if (log.resource_type?.startsWith('chat')) return `${action} cuộc chat`
    return action
}

function getFriendlyResourceTitle(log: AuditLogResponse, metadata: Record<string, unknown>) {
    const resourceType = log.resource_type || ''
    const documentName = getString(metadata.document_name)
    const folderName = getString(metadata.folder_name)
    const departmentName = getString(metadata.department_name)
    const conversationTitle = getString(metadata.conversation_title)
    const resourceName = getString(metadata.resource_name)
    const departmentHierarchy = getStringArray(metadata.department_hierarchy)
    const folderHierarchy = getStringArray(metadata.folder_hierarchy)

    if (resourceType.includes('chat') && conversationTitle) return `Cuộc chat: ${conversationTitle}`
    if (documentName) return `Tài liệu: ${documentName}`
    if (resourceType.includes('folder') && folderHierarchy.length > 0) return `Thư mục: ${folderHierarchy.join(' > ')}`
    if (resourceType.includes('folder') && folderName) return `Thư mục: ${folderName}`
    if (resourceType.includes('department') && departmentHierarchy.length > 0) return `Phòng ban: ${departmentHierarchy.join(' > ')}`
    if (resourceType.includes('department') && departmentName) return `Phòng ban: ${departmentName}`
    if ((resourceType.includes('user') || resourceType.includes('account')) && resourceName) return `Người dùng: ${resourceName}`
    if (resourceType.includes('role') && resourceName && !isSystemFallbackLabel(resourceName)) return `Vai trò: ${resourceName}`
    if ((resourceType.includes('permission') || resourceType === 'Permission') && resourceName && !isSystemFallbackLabel(resourceName)) return `Quyền hạn: ${resourceName}`
    if (resourceName && !isSystemFallbackLabel(resourceName)) return resourceName
    if (log.resource_label) {
        const cleanedLabel = cleanResourceLabel(log.resource_label)
        if (!isSystemFallbackLabel(cleanedLabel)) return cleanedLabel
    }
    return ''
}

function getFriendlyDetailLines(log: AuditLogResponse, metadata: Record<string, unknown>) {
    const lines: string[] = []
    const contextLabel = getString(metadata.context_label)
    const departmentName = getString(metadata.department_name)
    const folderName = getString(metadata.folder_name)
    const departmentHierarchy = getStringArray(metadata.department_hierarchy)
    const folderHierarchy = getStringArray(metadata.folder_hierarchy)
    const version = getNumber(metadata.version)

    if (contextLabel) {
        const normalizedContext = normalizeAuditText(contextLabel)
        if (normalizedContext === 'Xem tài liệu trong phòng ban' && departmentName) {
            lines.push(`Xem danh sách tài liệu của phòng ban: ${departmentName}`)
        } else if (normalizedContext === 'Xem tài liệu trong thư mục' && folderName) {
            lines.push(`Xem danh sách tài liệu trong thư mục: ${folderName}`)
        } else {
            lines.push(normalizedContext)
        }
    }
    if (departmentHierarchy.length > 1) lines.push(`Cây phòng ban: ${departmentHierarchy.join(' > ')}`)
    if (departmentName && !departmentHierarchy.includes(departmentName)) lines.push(`Phòng ban: ${departmentName}`)
    if (folderHierarchy.length > 0) lines.push(`Đường dẫn thư mục: ${folderHierarchy.join(' > ')}`)
    if (folderName && folderHierarchy.length === 0) lines.push(`Thư mục: ${folderName}`)
    if (version > 0) lines.push(`Phiên bản tài liệu: ${version}`)

    const question = getChatQuestion(log)
    if (question) lines.push(`Câu hỏi: "${question}"`)

    const bodySummary = getBodySummary(log)
    const documentCount = getNumber(bodySummary.document_ids_count) || getNumber(metadata.document_count)
    const folderCount = getNumber(bodySummary.folder_ids_count) || getNumber(metadata.folder_count)
    if (documentCount > 0) lines.push(`${documentCount} tài liệu được dùng làm ngữ cảnh`)
    if (folderCount > 0) lines.push(`${folderCount} thư mục được dùng làm ngữ cảnh`)

    return Array.from(new Set(lines.filter((line) => Boolean(line) && !hasTechnicalId(line) && !isSystemFallbackLabel(line)))).slice(0, 4)
}

function getResourceTitle(log: AuditLogResponse) {
    const metadata = asRecord(log.metadata)
    const friendlyTitle = getFriendlyResourceTitle(log, metadata)
    if (friendlyTitle) return friendlyTitle
    const fallbackTitle = getActionFallbackTitle(log)
    return (
        fallbackTitle ||
        log.resource_label ||
        getString(metadata.resource_label) ||
        getString(metadata.resource_name) ||
        getString(metadata.document_name) ||
        getString(metadata.folder_name) ||
        getString(metadata.department_name) ||
        getString(metadata.conversation_title) ||
        'Dá»¯ liá»‡u há»‡ thá»‘ng'
    )
}

function getDetailLines(log: AuditLogResponse) {
    const metadata = asRecord(log.metadata)
    const lines: string[] = []
    const friendlyLines = getFriendlyDetailLines(log, metadata)
    if (friendlyLines.length > 0) return friendlyLines

    const contextLabel = getString(metadata.context_label)
    if (contextLabel) lines.push(normalizeAuditText(contextLabel))

    const departmentHierarchy = getStringArray(metadata.department_hierarchy)
    const folderHierarchy = getStringArray(metadata.folder_hierarchy)
    const hierarchy = departmentHierarchy.length > 0 ? departmentHierarchy : folderHierarchy
    if (hierarchy.length > 0) lines.push(hierarchy.join(' > '))

    const question = getChatQuestion(log)
    if (question) lines.push(`Äang há»i: "${question}"`)

    return Array.from(new Set(lines.filter((line) => Boolean(line) && !hasTechnicalId(line) && !isSystemFallbackLabel(line)))).slice(0, 4)
}

function getApiLine(log: AuditLogResponse) {
    void log
    return ''
}

export default function AuditLogsPage() {
    const { hasPermission } = useRBAC()
    const canViewAudit = hasPermission('audit_log_view')

    const [logs, setLogs] = useState<AuditLogResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [totalItems, setTotalItems] = useState(0)
    const [username, setUsername] = useState('')
    const [selectedAccountId, setSelectedAccountId] = useState('')
    const [userOptions, setUserOptions] = useState<User[]>([])
    const [usersLoading, setUsersLoading] = useState(false)
    const [showUserOptions, setShowUserOptions] = useState(false)
    const [lastLoadedAt, setLastLoadedAt] = useState<Date | null>(null)

    const loadLogs = useCallback(async () => {
        if (!canViewAudit) return
        setLoading(true)
        setError(null)

        try {
            const response = await getAuditLogs({
                page,
                page_size: PAGE_SIZE,
                account_id: selectedAccountId || undefined,
                username: selectedAccountId ? undefined : username.trim() || undefined,
            })

            const payload = response.data
            const pagination = payload.pagination
            setLogs(payload.items || [])
            setTotalItems(pagination?.total_items || 0)
            setTotalPages(Math.max(pagination?.total_pages || 1, 1))
            setLastLoadedAt(new Date())
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Khong the tai nhat ky hoat dong'
            setError(message)
            setLogs([])
            setTotalItems(0)
            setTotalPages(1)
        } finally {
            setLoading(false)
        }
    }, [canViewAudit, page, selectedAccountId, username])

    useEffect(() => {
        const timer = window.setTimeout(() => {
            void loadLogs()
        }, 300)

        return () => window.clearTimeout(timer)
    }, [loadLogs])

    useEffect(() => {
        if (!canViewAudit || !showUserOptions) return

        const timer = window.setTimeout(() => {
            setUsersLoading(true)
            void getAllUsers(1, 8, username.trim() || undefined)
                .then((response) => setUserOptions(response.data || []))
                .catch(() => setUserOptions([]))
                .finally(() => setUsersLoading(false))
        }, 250)

        return () => window.clearTimeout(timer)
    }, [canViewAudit, showUserOptions, username])

    if (!canViewAudit) {
        return (
            <AccessDeniedPage
                title="Không có quyền xem nhật ký hoạt động"
                message="Bạn cần quyền audit_log_view để theo dõi hoạt động người dùng và trạng thái hệ thống."
            />
        )
    }

    return (
        <main className="min-h-screen bg-[#f8f9ff] p-4">
            <div className="mx-auto flex max-w-7xl flex-col gap-4">
                <section className="rounded-lg border border-slate-100 bg-white px-5 py-4 shadow-sm">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                        <div>
                            <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-[#fff7ed] px-2.5 py-1 text-xs font-bold text-[#b75b00]">
                                <AppIcon name="fact_check" className="h-4 w-4" />
                                Trung tâm giám sát hoạt động
                            </div>
                            <h1 className="text-2xl font-bold text-slate-950">Nhật ký hoạt động</h1>
                            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
                                Tìm và theo dõi hoạt động của người dùng theo tên đăng nhập.
                            </p>
                        </div>
                        <button
                            type="button"
                            onClick={() => void loadLogs()}
                            className="inline-flex h-10 items-center justify-center gap-2 rounded-full bg-[#b75b00] px-4 text-sm font-bold text-white hover:bg-[#9d4300]"
                        >
                            <AppIcon name="refresh" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                            Tải lại
                        </button>
                    </div>
                </section>

                <section className="rounded-lg border border-slate-100 bg-white p-4 shadow-sm">
                    <label className="relative block">
                        <span className="mb-1 block text-[11px] font-bold uppercase text-slate-400">
                            Tìm kiếm theo tên người dùng
                        </span>
                        <div className="flex h-11 items-center gap-2 rounded-lg border border-slate-200 px-3 focus-within:border-[#b75b00]">
                            <AppIcon name="search" className="h-4 w-4 text-slate-400" />
                            <input
                                value={username}
                                onChange={(event) => {
                                    setUsername(event.target.value)
                                    setSelectedAccountId('')
                                    setShowUserOptions(true)
                                    setPage(1)
                                }}
                                onFocus={() => setShowUserOptions(true)}
                                onBlur={() => window.setTimeout(() => setShowUserOptions(false), 160)}
                                placeholder="Nhập username..."
                                className="w-full bg-transparent text-sm font-semibold text-slate-700 outline-none placeholder:text-slate-400"
                            />
                            {username && (
                                <button
                                    type="button"
                                    onClick={() => {
                                        setUsername('')
                                        setSelectedAccountId('')
                                        setUserOptions([])
                                        setPage(1)
                                    }}
                                    className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-slate-50 hover:text-slate-700"
                                    aria-label="Xóa từ khóa"
                                >
                                    <AppIcon name="close" className="h-4 w-4" />
                                </button>
                            )}
                        </div>
                        {showUserOptions && (
                            <div className="absolute left-0 right-0 top-[74px] z-20 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg">
                                {usersLoading ? (
                                    <div className="px-4 py-3 text-sm font-semibold text-slate-400">Đang tìm người dùng...</div>
                                ) : userOptions.length > 0 ? (
                                    userOptions.map((user) => (
                                        <button
                                            key={user.account_id || user.id}
                                            type="button"
                                            onMouseDown={(event) => event.preventDefault()}
                                            onClick={() => {
                                                setUsername(user.username)
                                                setSelectedAccountId(user.account_id || user.id)
                                                setShowUserOptions(false)
                                                setPage(1)
                                            }}
                                            className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-[#fff7ed]"
                                        >
                                            <span className="min-w-0">
                                                <span className="block truncate text-sm font-bold text-slate-800">{user.username}</span>
                                                <span className="block truncate text-xs text-slate-400">
                                                    {user.full_name || user.email || user.department_name || 'Người dùng'}
                                                </span>
                                            </span>
                                            {selectedAccountId === (user.account_id || user.id) && (
                                                <AppIcon name="check" className="h-4 w-4 text-[#b75b00]" />
                                            )}
                                        </button>
                                    ))
                                ) : (
                                    <div className="px-4 py-3 text-sm font-semibold text-slate-400">Không tìm thấy người dùng</div>
                                )}
                            </div>
                        )}
                    </label>
                </section>

                <section className="min-w-0 overflow-hidden rounded-lg border border-slate-100 bg-white shadow-sm">
                    <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                        <div>
                            <h2 className="text-base font-bold text-slate-900">Hoạt động người dùng</h2>
                            <p className="text-xs text-slate-400">
                                {totalItems} bản ghi
                                {lastLoadedAt ? ` · cập nhật ${lastLoadedAt.toLocaleTimeString('vi-VN')}` : ''}
                            </p>
                        </div>
                        <div className="rounded-full bg-slate-50 px-3 py-1 text-xs font-bold text-slate-500">
                            Trang {page}/{totalPages}
                        </div>
                    </div>

                    {error && (
                        <div className="m-4 rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
                            {error}
                        </div>
                    )}

                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-100">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold uppercase text-slate-400">Thời gian</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold uppercase text-slate-400">Người dùng</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold uppercase text-slate-400">Tài nguyên truy cập</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold uppercase text-slate-400">Hành động</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold uppercase text-slate-400">Kết quả</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {loading ? (
                                    Array.from({ length: 8 }).map((_, rowIndex) => (
                                        <tr key={rowIndex}>
                                            {Array.from({ length: 5 }).map((__, cellIndex) => (
                                                <td key={cellIndex} className="px-4 py-3">
                                                    <div className="h-4 animate-pulse rounded bg-slate-100" />
                                                </td>
                                            ))}
                                        </tr>
                                    ))
                                ) : logs.length > 0 ? (
                                    logs.map((log) => {
                                        const detailLines = getDetailLines(log)
                                        const apiLine = getApiLine(log)
                                        const resourceTitle = getResourceTitle(log)

                                        return (
                                        <tr key={log.id} className="align-top hover:bg-[#fff7ed]/50">
                                            <td className="whitespace-nowrap px-4 py-4 text-xs font-semibold text-slate-600">
                                                {formatDateTime(log.created_at)}
                                            </td>
                                            <td className="px-4 py-4">
                                                <div className="max-w-[220px] truncate text-sm font-bold text-slate-800">
                                                    {getActorLabel(log)}
                                                </div>
                                            </td>
                                            <td className="px-4 py-4">
                                                <div className="max-w-[520px] text-sm font-bold leading-5 text-slate-800" title={log.activity_summary || resourceTitle}>
                                                    {resourceTitle}
                                                </div>
                                                <div className="hidden" title={log.activity_summary || resourceTitle}>
                                                    {log.resource_label || 'Dữ liệu hệ thống'}
                                                </div>
                                                {detailLines.length > 0 && (
                                                    <div className="mt-1 max-w-[560px] space-y-0.5 text-xs font-semibold leading-5 text-slate-500">
                                                        {detailLines.map((line) => (
                                                            <div key={line} className="line-clamp-2">{line}</div>
                                                        ))}
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-4 py-4">
                                                <div className="text-sm font-bold text-slate-800">{getActionText(log.action)}</div>
                                                {apiLine && (
                                                    <div className="mt-1 max-w-[320px] break-all font-mono text-[11px] font-semibold leading-4 text-slate-400">
                                                        {apiLine}
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-4 py-4">
                                                <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ring-1 ${STATUS_STYLE[log.status || ''] || 'bg-slate-50 text-slate-600 ring-slate-100'}`}>
                                                    {getStatusText(log.status)}
                                                </span>
                                            </td>
                                        </tr>
                                        )
                                    })
                                ) : (
                                    <tr>
                                        <td colSpan={5} className="px-4 py-12 text-center">
                                            <AppIcon name="inbox" className="mx-auto mb-2 h-8 w-8 text-slate-300" />
                                            <p className="text-sm font-bold text-slate-600">Không có hoạt động phù hợp</p>
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>

                    <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3">
                        <button
                            type="button"
                            disabled={page <= 1 || loading}
                            onClick={() => setPage((value) => Math.max(1, value - 1))}
                            className="rounded-full border border-slate-200 px-4 py-2 text-sm font-bold text-slate-600 disabled:opacity-50"
                        >
                            Trước
                        </button>
                        <span className="text-sm font-semibold text-slate-500">{totalItems} bản ghi</span>
                        <button
                            type="button"
                            disabled={page >= totalPages || loading}
                            onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                            className="rounded-full border border-slate-200 px-4 py-2 text-sm font-bold text-slate-600 disabled:opacity-50"
                        >
                            Sau
                        </button>
                    </div>
                </section>
            </div>
        </main>
    )
}
