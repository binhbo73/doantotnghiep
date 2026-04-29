'use client'

import React, { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '@/services/api'
import { FolderDocumentResponse, FolderResponse } from '@/services/folder'
import { fetchRoles } from '@/services/iam'
import {
    fetchDocumentPermissions,
    fetchFolderPermissions,
    grantDocumentPermission,
    grantFolderPermission,
    revokeDocumentPermission,
    revokeFolderPermission,
    PermissionItem,
    PermissionLevel,
    PermissionSubjectType,
} from '@/services/documentAcl'

interface DocumentPermissionsPanelProps {
    document?: FolderDocumentResponse | null
    folder?: FolderResponse | null
    title?: string
    mode?: PermissionDialogMode
    onPermissionChanged?: () => void | Promise<void>
    onPermissionGranted?: () => void | Promise<void>
}

type PermissionTarget = 'folder' | 'document'

type PermissionDialogMode = 'create' | 'detail'

type PermissionFormState = {
    target: PermissionTarget
    subjectType: PermissionSubjectType
    subjectId: string
    permission: PermissionLevel
}

type SubjectOption = {
    id: string
    label: string
}

type SubjectOptionsState = {
    accounts: SubjectOption[]
    roles: SubjectOption[]
    loading: boolean
    error: string | null
}

type PermissionViewState = {
    folderName: string
    folderScope: string
    folderPermissions: PermissionItem[]
    documentPermissions: PermissionItem[]
    folderTotal: number
    loading: boolean
    error: string | null
}

const DEFAULT_FORM_STATE: PermissionFormState = {
    target: 'folder',
    subjectType: 'account',
    subjectId: '',
    permission: 'read',
}

function formatDate(dateStr: string): string {
    try {
        return new Date(dateStr).toLocaleDateString('vi-VN', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
        })
    } catch {
        return dateStr
    }
}

function toSafeCount(value: unknown): number {
    const count = Number(value)
    return Number.isFinite(count) && count > 0 ? count : 0
}

function PermissionBadge({ permission }: { permission: PermissionLevel }) {
    const classes = {
        read: 'bg-sky-50 text-sky-700 border-sky-100',
        write: 'bg-amber-50 text-amber-700 border-amber-100',
        delete: 'bg-red-50 text-red-700 border-red-100',
    }

    return (
        <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold ${classes[permission]}`}>
            {permission}
        </span>
    )
}

function PermissionListItem({
    item,
    onRevoke,
    disabled,
    showRevoke = true,
}: {
    item: PermissionItem
    onRevoke: () => void
    disabled: boolean
    showRevoke?: boolean
}) {
    return (
        <div className="flex items-start gap-2.5 rounded-lg border border-slate-100 bg-slate-50/60 px-2.5 py-2.5">
            <div className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-md bg-white text-slate-400 shadow-sm ring-1 ring-slate-100">
                <span className="material-symbols-outlined text-sm">badge</span>
            </div>
            <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                    <p className="truncate text-[11px] font-semibold text-slate-800">
                        {item.subject_name || item.subject_id}
                    </p>
                    <span className="rounded-full bg-white px-1.5 py-0.5 text-[9px] font-medium text-slate-500 ring-1 ring-slate-200">
                        {item.subject_type}
                    </span>
                    <PermissionBadge permission={item.permission} />
                </div>
                {item.created_at && (
                    <p className="mt-0.5 text-[10px] text-slate-400">Ngày tạo: {formatDate(item.created_at)}</p>
                )}
            </div>
            {showRevoke && (
                <button
                    onClick={onRevoke}
                    disabled={disabled}
                    className="inline-flex items-center gap-1 rounded-md border border-red-200 bg-white px-2 py-1.5 text-[10px] font-semibold text-red-600 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                    <span className="material-symbols-outlined text-[14px]">remove_circle</span>
                    Thu hồi
                </button>
            )}
        </div>
    )
}

function EmptyPermissionState({ label }: { label: string }) {
    return (
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-center">
            <p className="text-xs font-semibold text-slate-600">Chưa có quyền {label}</p>
            <p className="mt-1 text-[11px] text-slate-400">Thêm quyền ở form phía trên để bắt đầu quản lý ACL.</p>
        </div>
    )
}

export function DocumentPermissionsPanel({ document, folder, title, mode = 'create', onPermissionChanged, onPermissionGranted }: DocumentPermissionsPanelProps) {
    const effectiveDocument = document || null
    const effectiveFolder = folder || null
    const [state, setState] = useState<PermissionViewState>({
        folderName: effectiveFolder?.name || '',
        folderScope: effectiveFolder?.access_scope || '',
        folderPermissions: [],
        documentPermissions: [],
        folderTotal: 0,
        loading: false,
        error: null,
    })
    const [form, setForm] = useState<PermissionFormState>(DEFAULT_FORM_STATE)
    const [saving, setSaving] = useState(false)
    const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
    const [subjectOptions, setSubjectOptions] = useState<SubjectOptionsState>({
        accounts: [],
        roles: [],
        loading: false,
        error: null,
    })
    const subjectOptionsLoadedRef = useRef(false)

    const folderId = effectiveFolder?.id || effectiveDocument?.folder || effectiveDocument?.folder_id || null

    useEffect(() => {
        if (!actionMessage) return

        const timer = window.setTimeout(() => setActionMessage(null), 2500)
        return () => window.clearTimeout(timer)
    }, [actionMessage])
    const documentId = effectiveDocument?.id || null
    const hasSelectedResource = Boolean(folderId || documentId)

    const loadSubjectOptions = async () => {
        if (subjectOptionsLoadedRef.current && subjectOptions.accounts.length > 0 && subjectOptions.roles.length > 0) {
            return
        }

        setSubjectOptions((prev) => ({ ...prev, loading: true, error: null }))

        const loadAllUsers = async () => {
            const collected: SubjectOption[] = []
            let page = 1
            let hasNext = true

            while (hasNext) {
                const response = await api.get<any>(`/accounts/?page=${page}&page_size=20`)
                const payload = response?.data?.data || response?.data || response
                const items = payload?.items || payload?.data || payload || []
                const pagination = payload?.pagination || response?.data?.pagination || response?.pagination || {}

                collected.push(
                    ...items
                        .filter((user: any) => user && (user.account_id || user.id))
                        .map((user: any) => ({
                            id: user.account_id || user.id,
                            label: user.full_name || `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username,
                        }))
                )

                hasNext = Boolean(pagination?.has_next || pagination?.has_next_page) || page < (pagination?.total_pages || 0)
                page += 1
            }

            return collected
        }

        const loadAllRoles = async () => {
            const collected: SubjectOption[] = []
            let page = 1
            let hasNext = true

            while (hasNext) {
                const response = await fetchRoles({ page, page_size: 20 })
                const responseData = response.data as any
                const items = Array.isArray(responseData) ? responseData : responseData?.items || []
                const pagination = responseData?.pagination || response.pagination

                collected.push(
                    ...items
                        .filter((role: any) => role && role.id)
                        .map((role: any) => ({
                            id: role.id,
                            label: role.name || role.code || role.id,
                        }))
                )

                hasNext = Boolean(pagination?.has_next) || page < (pagination?.total_pages || 0)
                page += 1
            }

            return collected
        }

        const [accountsResult, rolesResult] = await Promise.allSettled([
            loadAllUsers(),
            loadAllRoles(),
        ])

        const accounts = accountsResult.status === 'fulfilled' ? accountsResult.value : []
        const roles = rolesResult.status === 'fulfilled' ? rolesResult.value : []
        const accountError = accountsResult.status === 'rejected'
            ? accountsResult.reason instanceof Error
                ? accountsResult.reason.message
                : 'Không thể tải danh sách account'
            : null
        const roleError = rolesResult.status === 'rejected'
            ? rolesResult.reason instanceof Error
                ? rolesResult.reason.message
                : 'Không thể tải danh sách role'
            : null

        setSubjectOptions((prev) => ({
            accounts: accounts.length > 0 ? accounts : prev.accounts,
            roles: roles.length > 0 ? roles : prev.roles,
            loading: false,
            error: accountError || roleError,
        }))

        if (accounts.length > 0 && roles.length > 0) {
            subjectOptionsLoadedRef.current = true
        }
    }

    const loadPermissions = async () => {
        if (!folderId && !documentId) {
            setState({
                folderName: effectiveFolder?.name || '',
                folderScope: effectiveFolder?.access_scope || '',
                folderPermissions: [],
                documentPermissions: [],
                folderTotal: 0,
                loading: false,
                error: null,
            })
            return
        }

        setState((prev) => ({ ...prev, loading: true, error: null }))
        try {
            const [folderResponse, documentResponse] = await Promise.all([
                folderId ? fetchFolderPermissions(folderId) : Promise.resolve(null),
                documentId ? fetchDocumentPermissions(documentId) : Promise.resolve({ document_id: '', permissions: [] }),
            ])

            setState({
                folderName: folderResponse?.folder_name || effectiveFolder?.name || '',
                folderScope: folderResponse?.access_scope || effectiveFolder?.access_scope || '',
                folderPermissions: folderResponse?.permissions || [],
                documentPermissions: documentResponse.permissions || [],
                folderTotal: toSafeCount(folderResponse?.total_permissions),
                loading: false,
                error: null,
            })
        } catch (error) {
            setState((prev) => ({
                ...prev,
                loading: false,
                error: error instanceof Error ? error.message : 'Không thể tải danh sách quyền',
            }))
        }
    }

    useEffect(() => {
        loadPermissions()
        if (mode === 'create' && hasSelectedResource && !subjectOptionsLoadedRef.current) {
            loadSubjectOptions()
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [documentId, folderId, mode])

    const activeSubjectOptions = form.subjectType === 'account' ? subjectOptions.accounts : subjectOptions.roles

    const submitGrant = async () => {
        if (!form.subjectId.trim()) {
            setState((prev) => ({ ...prev, error: 'Vui lòng nhập subject_id trước khi cấp quyền' }))
            return
        }

        if (!folderId && !documentId) {
            setState((prev) => ({ ...prev, error: 'Không có folder hoặc document đính kèm để cấp quyền' }))
            return
        }

        setSaving(true)
        setState((prev) => ({ ...prev, error: null }))
        try {
            const payload = {
                subject_type: form.subjectType,
                subject_id: form.subjectId.trim(),
                permission: form.permission,
            }

            if (folderId && !documentId) {
                await grantFolderPermission(folderId, payload)
            } else if (documentId) {
                await grantDocumentPermission(documentId, payload)
            } else {
                throw new Error('Không xác định được tài nguyên để cấp quyền')
            }

            setForm((prev) => ({ ...prev, subjectId: '' }))
            await loadPermissions()
            await onPermissionChanged?.()
            setActionMessage({ type: 'success', text: 'Đã cấp quyền thành công' })
            await onPermissionGranted?.()
        } catch (error) {
            setActionMessage(null)
            setState((prev) => ({
                ...prev,
                error: error instanceof Error ? error.message : 'Không thể cấp quyền',
            }))
        } finally {
            setSaving(false)
        }
    }

    const handleRevoke = async (item: PermissionItem, target: PermissionTarget) => {
        if (target === 'folder' && !folderId) return

        setSaving(true)
        setState((prev) => ({ ...prev, error: null }))
        try {
            if (target === 'folder' && folderId) {
                await revokeFolderPermission(folderId, item.subject_type, item.subject_id, item.permission)
            } else if (documentId) {
                await revokeDocumentPermission(documentId, item.subject_type, item.subject_id, item.permission)
            }

            await loadPermissions()
            await onPermissionChanged?.()
            setActionMessage({ type: 'success', text: 'Đã cập nhật danh sách quyền' })
        } catch (error) {
            setActionMessage(null)
            setState((prev) => ({
                ...prev,
                error: error instanceof Error ? error.message : 'Không thể thu hồi quyền',
            }))
        } finally {
            setSaving(false)
        }
    }

    const renderPermissionSection = (label: string, permissions: PermissionItem[], emptyLabel: string) => (
        <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
                <div>
                    <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">{label}</p>
                    <p className="mt-1 text-[12px] font-semibold text-slate-700">{permissions.length} quyền</p>
                </div>
            </div>

            <div className="mt-3 space-y-2">
                {permissions.length > 0 ? (
                    permissions.map((item) => (
                        <PermissionListItem
                            key={item.id}
                            item={item}
                            onRevoke={() => { }}
                            disabled={true}
                            showRevoke={false}
                        />
                    ))
                ) : (
                    <EmptyPermissionState label={emptyLabel} />
                )}
            </div>
        </div>
    )

    const folderCountLabel = useMemo(() => {
        if (!folderId) return 'Không có folder'
        return `${state.folderTotal} quyền`
    }, [folderId, state.folderTotal])

    return (
        <div className="space-y-4">
            <div className="rounded-xl border border-slate-100 bg-gradient-to-br from-white to-slate-50 p-3 shadow-sm">
                <div className="flex items-center justify-between gap-2.5">
                    <div>
                        <h4 className="mt-1 text-[13px] font-bold text-slate-900">{title || (effectiveDocument ? (effectiveDocument.original_name || effectiveDocument.filename) : (effectiveFolder?.name || 'Quản lý quyền truy cập'))}</h4>
                        <p className="mt-1 text-[10px] font-medium uppercase tracking-[0.14em] text-slate-400">
                            {mode === 'detail' ? 'Xem chi tiết quyền' : 'Cấp quyền mới'}
                        </p>
                    </div>
                    <button
                        onClick={loadPermissions}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[10px] font-semibold text-slate-600 transition-colors hover:bg-slate-50"
                    >
                        <span className="material-symbols-outlined text-[14px]">refresh</span>
                        Làm mới
                    </button>
                </div>

                {actionMessage && (
                    <div
                        className={`mt-3 rounded-lg border px-3 py-2 text-[11px] font-medium ${actionMessage.type === 'success'
                            ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                            : 'border-red-200 bg-red-50 text-red-700'
                            }`}
                    >
                        {actionMessage.text}
                    </div>
                )}

                <div className="mt-3 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                    <div className="rounded-lg border border-[#f97316]/10 bg-[#fef5ed] p-2.5">
                        <p className="text-[9px] font-bold uppercase tracking-wider text-[#9d4300]/70">Cấp quyền thư mục</p>
                        <p className="mt-1 truncate text-[11px] font-semibold text-[#9d4300]">{state.folderName || effectiveFolder?.name || 'Chưa chọn thư mục'}</p>
                        <p className="text-[10px] capitalize text-[#9d4300]/60">{state.folderScope || effectiveFolder?.access_scope || 'N/A'}</p>
                        <p className="mt-1.5 text-[10px] font-medium text-[#9d4300]/70">{folderCountLabel}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-white p-2.5">
                        <p className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Cấp quyền tài liệu</p>
                        <p className="mt-1 truncate text-[11px] font-semibold text-slate-700">{effectiveDocument ? (effectiveDocument.original_name || effectiveDocument.filename) : 'Chưa chọn tài liệu'}</p>
                        <p className="text-[10px] text-slate-400">{state.documentPermissions.length} quyền</p>
                    </div>
                </div>

                {mode === 'detail' ? (
                    <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
                        {renderPermissionSection('Cấp quyền thư mục', state.folderPermissions, 'folder')}
                        {renderPermissionSection('Cấp quyền tài liệu', state.documentPermissions, 'document')}
                    </div>
                ) : (
                    <div className="mt-3 rounded-xl border border-slate-100 bg-white p-3 shadow-sm">
                        {!hasSelectedResource ? (
                            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-center">
                                <p className="text-xs font-semibold text-slate-600">Chưa chọn thư mục hoặc tài liệu</p>
                                <p className="mt-1 text-[11px] text-slate-400">Chọn tài nguyên ở phía trên trước khi cấp quyền.</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
                                <label className="space-y-1">
                                    <span className="text-[10px] font-semibold text-slate-500">Loại subject</span>
                                    <select
                                        value={form.subjectType}
                                        onChange={(e) => setForm((prev) => ({
                                            ...prev,
                                            subjectType: e.target.value as PermissionSubjectType,
                                            subjectId: '',
                                        }))}
                                        className="w-full rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-[13px] text-slate-700 outline-none transition focus:border-[#9d4300]"
                                    >
                                        <option value="account">Account</option>
                                        <option value="role">Role</option>
                                    </select>
                                </label>

                                <label className="space-y-1 md:col-span-2">
                                    <span className="text-[10px] font-semibold text-slate-500">
                                        {form.subjectType === 'account' ? 'Chọn người dùng' : 'Chọn vai trò'}
                                    </span>
                                    <select
                                        value={form.subjectId}
                                        onChange={(e) => setForm((prev) => ({ ...prev, subjectId: e.target.value }))}
                                        disabled={subjectOptions.loading}
                                        className="w-full rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-[13px] text-slate-700 outline-none transition focus:border-[#9d4300] disabled:bg-slate-50 disabled:text-slate-400"
                                    >
                                        <option value="">
                                            {subjectOptions.loading
                                                ? 'Đang tải danh sách...'
                                                : form.subjectType === 'account'
                                                    ? 'Chọn account theo tên'
                                                    : 'Chọn role theo tên'}
                                        </option>
                                        {activeSubjectOptions.map((option) => (
                                            <option key={option.id} value={option.id}>
                                                {option.label}
                                            </option>
                                        ))}
                                    </select>
                                    {subjectOptions.error && (
                                        <p className="text-[11px] text-amber-600">{subjectOptions.error}</p>
                                    )}
                                </label>

                                <label className="space-y-1">
                                    <span className="text-[10px] font-semibold text-slate-500">Quyền</span>
                                    <select
                                        value={form.permission}
                                        onChange={(e) => setForm((prev) => ({ ...prev, permission: e.target.value as PermissionLevel }))}
                                        className="w-full rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-[13px] text-slate-700 outline-none transition focus:border-[#9d4300]"
                                    >
                                        <option value="read">read</option>
                                        <option value="write">write</option>
                                        <option value="delete">delete</option>
                                    </select>
                                </label>

                                <div className="flex items-end">
                                    <button
                                        onClick={submitGrant}
                                        disabled={saving}
                                        className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-[#9d4300] px-3 py-2 text-[13px] font-bold text-white transition-colors hover:bg-[#b75b00] disabled:cursor-not-allowed disabled:opacity-70"
                                    >
                                        <span className="material-symbols-outlined text-sm">add_circle</span>
                                        Gán quyền
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {state.error && (
                    <div className="mt-2.5 rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-[11px] text-red-700">
                        {state.error}
                    </div>
                )}
            </div>


        </div>
    )
}
