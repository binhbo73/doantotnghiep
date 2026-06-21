'use client'

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { AccessDeniedPage } from '@/components/common/AccessDeniedPage'
import { AppIcon } from '@/components/ui/AppIcon'
import { useRBAC } from '@/hooks/useRBAC'
import {
    DeletedRecord,
    DeletedResource,
    listDeletedRecords,
    restoreDeletedRecord,
} from '@/services/restore'

type ResourceGroup = 'Accounts' | 'Documents' | 'Chat' | 'System'

type ResourceConfig = {
    key: DeletedResource
    label: string
    description: string
    permission: string
    group: ResourceGroup
}

const RESOURCE_CONFIGS: ResourceConfig[] = [
    { key: 'accounts', label: 'T\u00e0i kho\u1ea3n', description: 'T\u00e0i kho\u1ea3n \u0111\u0103ng nh\u1eadp \u0111\u00e3 b\u1ecb x\u00f3a m\u1ec1m', permission: 'user_delete', group: 'Accounts' },
    { key: 'user_profiles', label: 'H\u1ed3 s\u01a1 ng\u01b0\u1eddi d\u00f9ng', description: 'H\u1ed3 s\u01a1 g\u1eafn v\u1edbi t\u00e0i kho\u1ea3n', permission: 'user_delete', group: 'Accounts' },
    { key: 'password_reset_tokens', label: 'M\u00e3 \u0111\u1eb7t l\u1ea1i m\u1eadt kh\u1ea9u', description: 'M\u00e3 \u0111\u1eb7t l\u1ea1i m\u1eadt kh\u1ea9u \u0111\u00e3 b\u1ecb x\u00f3a m\u1ec1m', permission: 'user_reset_password', group: 'Accounts' },
    { key: 'account_roles', label: 'Vai tr\u00f2 t\u00e0i kho\u1ea3n', description: 'Li\u00ean k\u1ebft vai tr\u00f2 c\u1ee7a t\u00e0i kho\u1ea3n \u0111\u00e3 b\u1ecb thu h\u1ed3i', permission: 'user_change_role', group: 'Accounts' },
    { key: 'departments', label: 'Ph\u00f2ng ban', description: 'Ph\u00f2ng ban \u0111\u00e3 b\u1ecb x\u00f3a m\u1ec1m', permission: 'department_manage', group: 'Accounts' },
    { key: 'roles', label: 'Vai tr\u00f2', description: 'Vai tr\u00f2 t\u00f9y ch\u1ec9nh \u0111\u00e3 b\u1ecb x\u00f3a m\u1ec1m', permission: 'role_manage', group: 'Accounts' },
    { key: 'permissions', label: 'Quy\u1ec1n h\u1ea1n', description: 'M\u00e3 quy\u1ec1n \u0111\u00e3 b\u1ecb x\u00f3a m\u1ec1m', permission: 'permission_manage', group: 'Accounts' },
    { key: 'role_permissions', label: 'Quy\u1ec1n c\u1ee7a vai tr\u00f2', description: 'Li\u00ean k\u1ebft quy\u1ec1n c\u1ee7a vai tr\u00f2 \u0111\u00e3 b\u1ecb thu h\u1ed3i', permission: 'role_manage', group: 'Accounts' },
    { key: 'companies', label: 'C\u00f4ng ty', description: 'B\u1ea3n ghi c\u1ea5u h\u00ecnh c\u00f4ng ty', permission: 'system_admin', group: 'System' },

    { key: 'folders', label: 'Th\u01b0 m\u1ee5c', description: 'Th\u01b0 m\u1ee5c \u0111\u00e3 b\u1ecb x\u00f3a m\u1ec1m', permission: 'folder_delete', group: 'Documents' },
    { key: 'folder_permissions', label: 'Quy\u1ec1n th\u01b0 m\u1ee5c', description: 'Quy\u1ec1n truy c\u1eadp th\u01b0 m\u1ee5c \u0111\u00e3 b\u1ecb thu h\u1ed3i', permission: 'folder_update', group: 'Documents' },
    { key: 'tags', label: 'Th\u1ebb', description: 'Th\u1ebb t\u00e0i li\u1ec7u \u0111\u00e3 b\u1ecb x\u00f3a m\u1ec1m', permission: 'document_update', group: 'Documents' },
    { key: 'documents', label: 'T\u00e0i li\u1ec7u', description: 'T\u00e0i li\u1ec7u \u0111\u00e3 b\u1ecb x\u00f3a m\u1ec1m', permission: 'document_delete', group: 'Documents' },
    { key: 'document_chunks', label: '\u0110o\u1ea1n n\u1ed9i dung', description: '\u0110o\u1ea1n n\u1ed9i dung RAG', permission: 'document_delete', group: 'Documents' },
    { key: 'chunk_revision_links', label: 'Li\u00ean k\u1ebft phi\u00ean b\u1ea3n \u0111o\u1ea1n', description: 'B\u1ea3n ghi l\u1ecbch s\u1eed phi\u00ean b\u1ea3n c\u1ee7a \u0111o\u1ea1n n\u1ed9i dung', permission: 'document_delete', group: 'Documents' },
    { key: 'document_permissions', label: 'Quy\u1ec1n t\u00e0i li\u1ec7u', description: 'Quy\u1ec1n truy c\u1eadp t\u00e0i li\u1ec7u \u0111\u00e3 b\u1ecb thu h\u1ed3i', permission: 'document_share', group: 'Documents' },
    { key: 'document_embeddings', label: 'Vector nh\u00fang t\u00e0i li\u1ec7u', description: 'B\u1ea3n ghi metadata embedding', permission: 'document_delete', group: 'Documents' },
    { key: 'document_assets', label: 'T\u1ec7p tr\u00edch xu\u1ea5t', description: 'T\u1ec7p \u0111\u01b0\u1ee3c tr\u00edch xu\u1ea5t t\u1eeb t\u00e0i li\u1ec7u', permission: 'document_delete', group: 'Documents' },

    { key: 'conversations', label: 'Cu\u1ed9c tr\u00f2 chuy\u1ec7n', description: 'Cu\u1ed9c tr\u00f2 chuy\u1ec7n \u0111\u00e3 b\u1ecb x\u00f3a m\u1ec1m', permission: 'chat_create', group: 'Chat' },
    { key: 'conversation_documents', label: 'T\u00e0i li\u1ec7u trong chat', description: 'T\u00e0i li\u1ec7u \u0111\u00ednh k\u00e8m trong chat', permission: 'chat_create', group: 'Chat' },
    { key: 'conversation_folders', label: 'Th\u01b0 m\u1ee5c trong chat', description: 'Th\u01b0 m\u1ee5c \u0111\u00ednh k\u00e8m trong chat', permission: 'chat_create', group: 'Chat' },
    { key: 'messages', label: 'Tin nh\u1eafn', description: 'Tin nh\u1eafn chat \u0111\u00e3 b\u1ecb x\u00f3a m\u1ec1m', permission: 'chat_send', group: 'Chat' },
    { key: 'human_feedback', label: 'Ph\u1ea3n h\u1ed3i ng\u01b0\u1eddi d\u00f9ng', description: 'Ph\u1ea3n h\u1ed3i AI \u0111\u00e3 b\u1ecb x\u00f3a m\u1ec1m', permission: 'chat_send', group: 'Chat' },

    { key: 'audit_logs', label: 'Nh\u1eadt k\u00fd ki\u1ec3m to\u00e1n', description: 'Nh\u1eadt k\u00fd ki\u1ec3m to\u00e1n \u0111\u00e3 b\u1ecb x\u00f3a m\u1ec1m', permission: 'audit_log_view', group: 'System' },
    { key: 'async_tasks', label: 'T\u00e1c v\u1ee5 n\u1ec1n', description: 'T\u00e1c v\u1ee5 ch\u1ea1y n\u1ec1n \u0111\u00e3 b\u1ecb x\u00f3a m\u1ec1m', permission: 'system_admin', group: 'System' },
    { key: 'user_document_caches', label: 'B\u1ed9 nh\u1edb \u0111\u1ec7m t\u00e0i li\u1ec7u', description: 'B\u1ea3n ghi cache quy\u1ec1n truy c\u1eadp t\u00e0i li\u1ec7u', permission: 'system_admin', group: 'System' },
]

const PAGE_SIZE = 20

const HIDDEN_DELETED_RESOURCES = new Set<DeletedResource>([
    'companies',
    'tags',
    'document_chunks',
    'document_embeddings',
    'document_assets',
    'human_feedback',
    'audit_logs',
    'async_tasks',
    'user_document_caches',
])

const RESOURCE_GROUP_LABELS: Record<ResourceGroup, string> = {
    Accounts: 'T\u00e0i kho\u1ea3n',
    Documents: 'T\u00e0i li\u1ec7u',
    Chat: 'Chat',
    System: 'H\u1ec7 th\u1ed1ng',
}

const RESOURCE_TYPE_ALIASES: Record<string, DeletedResource> = {
    account: 'accounts',
    user_profile: 'user_profiles',
    password_reset_token: 'password_reset_tokens',
    account_role: 'account_roles',
    department: 'departments',
    role: 'roles',
    permission: 'permissions',
    role_permission: 'role_permissions',
    company: 'companies',
    folder: 'folders',
    folder_permission: 'folder_permissions',
    tag: 'tags',
    document: 'documents',
    document_chunk: 'document_chunks',
    chunk_revision_link: 'chunk_revision_links',
    document_permission: 'document_permissions',
    document_embedding: 'document_embeddings',
    document_asset: 'document_assets',
    conversation: 'conversations',
    conversation_document: 'conversation_documents',
    conversation_folder: 'conversation_folders',
    message: 'messages',
    human_feedback: 'human_feedback',
    audit_log: 'audit_logs',
    async_task: 'async_tasks',
    user_document_cache: 'user_document_caches',
}

function formatDate(value?: string | null) {
    if (!value) return 'Kh\u00f4ng x\u00e1c \u0111\u1ecbnh'
    try {
        return new Date(value).toLocaleString('vi-VN', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        })
    } catch {
        return value
    }
}

function getResourceDisplayName(resourceType: string) {
    const resourceKey = RESOURCE_TYPE_ALIASES[resourceType] || resourceType
    return RESOURCE_CONFIGS.find((item) => item.key === resourceKey)?.label || resourceType
}

function translateRestoreError(message: string) {
    if (message === 'Unsupported deleted resource' || message === 'Unsupported restore resource') {
        return 'Lo\u1ea1i d\u1eef li\u1ec7u n\u00e0y kh\u00f4ng \u0111\u01b0\u1ee3c h\u1ed7 tr\u1ee3'
    }
    if (message === 'You do not have permission to view deleted records') {
        return 'B\u1ea1n kh\u00f4ng c\u00f3 quy\u1ec1n xem c\u00e1c b\u1ea3n ghi \u0111\u00e3 x\u00f3a'
    }
    if (message === 'You do not have permission to restore this resource') {
        return 'B\u1ea1n kh\u00f4ng c\u00f3 quy\u1ec1n kh\u00f4i ph\u1ee5c lo\u1ea1i d\u1eef li\u1ec7u n\u00e0y'
    }
    if (/^Deleted .+ not found$/.test(message)) {
        return 'Kh\u00f4ng t\u00ecm th\u1ea5y b\u1ea3n ghi \u0111\u00e3 x\u00f3a'
    }
    if (/^.+ is already active$/.test(message)) {
        return 'B\u1ea3n ghi n\u00e0y \u0111\u00e3 \u0111\u01b0\u1ee3c kh\u00f4i ph\u1ee5c'
    }
    if (/^Cannot restore .+ because its .+ no longer exists$/.test(message)) {
        return 'Kh\u00f4ng th\u1ec3 kh\u00f4i ph\u1ee5c v\u00ec b\u1ea3n ghi li\u00ean quan kh\u00f4ng c\u00f2n t\u1ed3n t\u1ea1i'
    }
    if (/^Cannot restore .+ while its .+ is deleted$/.test(message)) {
        return 'Kh\u00f4ng th\u1ec3 kh\u00f4i ph\u1ee5c khi b\u1ea3n ghi li\u00ean quan v\u1eabn \u0111ang b\u1ecb x\u00f3a'
    }
    if (/^Cannot restore .+ with unsupported subject type/.test(message)) {
        return 'Kh\u00f4ng th\u1ec3 kh\u00f4i ph\u1ee5c v\u00ec lo\u1ea1i \u0111\u1ed1i t\u01b0\u1ee3ng li\u00ean quan kh\u00f4ng \u0111\u01b0\u1ee3c h\u1ed7 tr\u1ee3'
    }
    if (/^Cannot restore .+ because its .+ subject no longer exists$/.test(message)) {
        return 'Kh\u00f4ng th\u1ec3 kh\u00f4i ph\u1ee5c v\u00ec \u0111\u1ed1i t\u01b0\u1ee3ng li\u00ean quan kh\u00f4ng c\u00f2n t\u1ed3n t\u1ea1i'
    }
    if (/^Cannot restore .+ while its .+ subject is deleted$/.test(message)) {
        return 'Kh\u00f4ng th\u1ec3 kh\u00f4i ph\u1ee5c khi \u0111\u1ed1i t\u01b0\u1ee3ng li\u00ean quan v\u1eabn \u0111ang b\u1ecb x\u00f3a'
    }
    return message
}

export default function DeletedRecordsPage() {
    const { hasPermission } = useRBAC()
    const [selectedResource, setSelectedResource] = useState<DeletedResource>('documents')
    const [records, setRecords] = useState<DeletedRecord[]>([])
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [totalItems, setTotalItems] = useState(0)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [restoringId, setRestoringId] = useState<string | null>(null)
    const [resourceSearch, setResourceSearch] = useState('')
    const [resourceCounts, setResourceCounts] = useState<Partial<Record<DeletedResource, number>>>({})
    const [isLoadingCounts, setIsLoadingCounts] = useState(false)

    const visibleResources = useMemo(
        () => RESOURCE_CONFIGS.filter((item) => !HIDDEN_DELETED_RESOURCES.has(item.key) && hasPermission(item.permission)),
        [hasPermission]
    )

    const visibleResourceKeys = visibleResources.map((item) => item.key).join('|')

    const canAccessRestoreCenter = hasPermission('system_admin')

    const selectedConfig = useMemo(
        () => RESOURCE_CONFIGS.find((item) => item.key === selectedResource) || RESOURCE_CONFIGS[0],
        [selectedResource]
    )

    const filteredResources = useMemo(() => {
        const keyword = resourceSearch.trim().toLowerCase()
        if (!keyword) return visibleResources

        return visibleResources.filter((item) => {
            const searchable = `${item.label} ${item.description} ${item.key}`.toLowerCase()
            return searchable.includes(keyword)
        })
    }, [resourceSearch, visibleResources])

    const totalDeletedCount = useMemo(() => {
        return visibleResources.reduce((total, item) => total + (resourceCounts[item.key] || 0), 0)
    }, [resourceCounts, visibleResources])

    useEffect(() => {
        if (visibleResources.length === 0) return
        if (!visibleResources.some((item) => item.key === selectedResource)) {
            setSelectedResource(visibleResources[0].key)
            setPage(1)
        }
    }, [selectedResource, visibleResources])

    const loadDeletedRecords = useCallback(async () => {
        if (!canAccessRestoreCenter || visibleResources.length === 0) {
            setIsLoading(false)
            return
        }

        setIsLoading(true)
        setError(null)

        try {
            const result = await listDeletedRecords(selectedResource, page, PAGE_SIZE)
            setRecords(result.items)
            setTotalItems(result.total_items)
            setTotalPages(Math.max(result.total_pages || 1, 1))
            setResourceCounts((current) => ({
                ...current,
                [selectedResource]: result.total_items,
            }))
        } catch (err) {
            const message = err instanceof Error ? translateRestoreError(err.message) : 'Kh\u00f4ng th\u1ec3 t\u1ea3i d\u1eef li\u1ec7u \u0111\u00e3 x\u00f3a'
            setError(message)
            setRecords([])
            setTotalItems(0)
            setTotalPages(1)
        } finally {
            setIsLoading(false)
        }
    }, [canAccessRestoreCenter, page, selectedResource, visibleResources.length])

    useEffect(() => {
        void loadDeletedRecords()
    }, [loadDeletedRecords])

    const loadResourceCounts = useCallback(async () => {
        if (!canAccessRestoreCenter || !visibleResourceKeys) return

        const resources = visibleResourceKeys.split('|') as DeletedResource[]

        setIsLoadingCounts(true)
        try {
            const results = await Promise.allSettled(
                resources.map(async (resource) => {
                    const result = await listDeletedRecords(resource, 1, 1)
                    return [resource, result.total_items] as const
                })
            )

            setResourceCounts((current) => {
                const next = { ...current }
                results.forEach((result) => {
                    if (result.status === 'fulfilled') {
                        const [key, count] = result.value
                        next[key] = count
                    }
                })
                return next
            })
        } finally {
            setIsLoadingCounts(false)
        }
    }, [canAccessRestoreCenter, visibleResourceKeys])

    useEffect(() => {
        void loadResourceCounts()
    }, [loadResourceCounts])

    const groupedResources = useMemo(() => {
        return filteredResources.reduce<Record<ResourceGroup, ResourceConfig[]>>((groups, item) => {
            groups[item.group] = groups[item.group] || []
            groups[item.group].push(item)
            return groups
        }, {} as Record<ResourceGroup, ResourceConfig[]>)
    }, [filteredResources])

    const handleSelectResource = (resource: DeletedResource) => {
        setSelectedResource(resource)
        setPage(1)
    }

    const handleRestore = async (record: DeletedRecord) => {
        if (restoringId) return
        if (!window.confirm(`Kh\u00f4i ph\u1ee5c "${record.name}"?`)) return

        setRestoringId(record.id)
        try {
            await restoreDeletedRecord(selectedResource, record.id)
            toast.success(`\u0110\u00e3 kh\u00f4i ph\u1ee5c "${record.name}"`)
            await loadDeletedRecords()
            void loadResourceCounts()
        } catch (err) {
            const message = err instanceof Error ? translateRestoreError(err.message) : 'Kh\u00f4ng th\u1ec3 kh\u00f4i ph\u1ee5c b\u1ea3n ghi'
            toast.error(message)
        } finally {
            setRestoringId(null)
        }
    }

    if (!canAccessRestoreCenter) {
        return (
            <AccessDeniedPage
                title="Kh\u00f4ng c\u00f3 quy\u1ec1n kh\u00f4i ph\u1ee5c"
                message="B\u1ea1n c\u1ea7n quy\u1ec1n kh\u00f4i ph\u1ee5c c\u1ee7a qu\u1ea3n tr\u1ecb vi\u00ean \u0111\u1ec3 xem v\u00e0 kh\u00f4i ph\u1ee5c c\u00e1c b\u1ea3n ghi \u0111\u00e3 x\u00f3a m\u1ec1m."
            />
        )
    }

    return (
        <div className="min-h-screen bg-[#f8f9ff] p-3 sm:p-4">
            <div className="mx-auto flex max-w-7xl flex-col gap-4 lg:h-[calc(100vh-2rem)]">
                <section className="shrink-0 rounded-[1.5rem] bg-white px-5 py-4 shadow-sm ring-1 ring-slate-100">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                        <div>
                            <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-[#fff7ed] px-2.5 py-1 text-xs font-semibold text-[#b75b00]">
                                <AppIcon name="restore" className="h-3.5 w-3.5" />
                                {'Trung t\u00e2m kh\u00f4i ph\u1ee5c d\u1eef li\u1ec7u'}
                            </div>
                            <h1 className="text-xl font-bold text-slate-900 sm:text-2xl">{'Kh\u00f4i ph\u1ee5c d\u1eef li\u1ec7u \u0111\u00e3 x\u00f3a'}</h1>
                            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
                                {'Xem l\u1ea1i c\u00e1c b\u1ea3n ghi \u0111\u00e3 x\u00f3a m\u1ec1m v\u00e0 kh\u00f4i ph\u1ee5c khi c\u1ea7n. Vi\u1ec7c kh\u00f4i ph\u1ee5c s\u1ebd b\u1ecb ch\u1eb7n n\u1ebfu b\u1ea3n ghi cha b\u1eaft bu\u1ed9c v\u1eabn \u0111ang b\u1ecb x\u00f3a.'}
                            </p>
                        </div>
                        <button
                            onClick={() => {
                                void loadDeletedRecords()
                                void loadResourceCounts()
                            }}
                            disabled={isLoading || isLoadingCounts}
                            className="inline-flex items-center justify-center gap-2 rounded-3xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
                        >
                            <AppIcon name="refresh" className={`h-4 w-4 ${isLoading || isLoadingCounts ? 'animate-spin' : ''}`} />
                            {'T\u1ea3i l\u1ea1i'}
                        </button>
                    </div>
                </section>

                <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-12">
                    <aside className="min-h-0 lg:col-span-4 xl:col-span-3">
                        <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-[1.35rem] bg-white shadow-sm ring-1 ring-slate-100">
                            <div className="shrink-0 border-b border-slate-100 px-4 py-3">
                                <p className="text-sm font-bold text-slate-800">{'Lo\u1ea1i d\u1eef li\u1ec7u'}</p>
                                <p className="mt-1 text-xs text-slate-400">
                                    {visibleResources.length} {'lo\u1ea1i'} · {totalDeletedCount} {'b\u1ea3n ghi \u0111\u00e3 x\u00f3a'}
                                </p>
                                <label className="mt-2.5 flex items-center gap-2 rounded-2xl bg-slate-50 px-3 py-2 text-slate-400 ring-1 ring-slate-100 focus-within:bg-white focus-within:ring-[#cfe0ff]">
                                    <AppIcon name="search" className="h-4 w-4" />
                                    <input
                                        value={resourceSearch}
                                        onChange={(event) => setResourceSearch(event.target.value)}
                                        placeholder={'T\u00ecm lo\u1ea1i d\u1eef li\u1ec7u...'}
                                        className="w-full bg-transparent text-sm font-medium text-slate-700 outline-none placeholder:text-slate-400"
                                    />
                                </label>
                            </div>
                            <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-3 py-3">
                                {filteredResources.length === 0 ? (
                                    <div className="rounded-2xl bg-slate-50 px-4 py-6 text-center text-sm font-medium text-slate-500">
                                        {'Kh\u00f4ng t\u00ecm th\u1ea5y lo\u1ea1i d\u1eef li\u1ec7u ph\u00f9 h\u1ee3p'}
                                    </div>
                                ) : Object.entries(groupedResources).map(([group, items]) => (
                                    <div key={group}>
                                        <p className="mb-1.5 px-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">{RESOURCE_GROUP_LABELS[group as ResourceGroup]}</p>
                                        <div className="space-y-1">
                                            {items.map((item) => {
                                                const active = item.key === selectedResource
                                                return (
                                                    <button
                                                        key={item.key}
                                                        onClick={() => handleSelectResource(item.key)}
                                                        className={`w-full rounded-xl px-3 py-2 text-left transition ${active ? 'bg-[#fff7ed] text-[#b75b00] shadow-sm ring-1 ring-[#fed7aa]' : 'text-slate-600 hover:bg-slate-50'}`}
                                                    >
                                                        <div className="flex items-center justify-between gap-2">
                                                            <div className="min-w-0 truncate text-sm font-semibold leading-5">{item.label}</div>
                                                            <span
                                                                className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-bold ${active
                                                                    ? 'bg-white/80 text-[#b75b00]'
                                                                    : (resourceCounts[item.key] || 0) > 0
                                                                        ? 'bg-[#fff7ed] text-[#b75b00]'
                                                                        : 'bg-slate-100 text-slate-400'
                                                                    }`}
                                                                title={'S\u1ed1 b\u1ea3n ghi \u0111\u00e3 x\u00f3a'}
                                                            >
                                                                {isLoadingCounts && resourceCounts[item.key] === undefined ? '...' : resourceCounts[item.key] ?? 0}
                                                            </span>
                                                        </div>
                                                        <div className="mt-0.5 line-clamp-1 text-xs text-slate-400">{item.description}</div>
                                                    </button>
                                                )
                                            })}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </aside>

                    <section className="min-h-0 lg:col-span-8 xl:col-span-9">
                        <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-[1.35rem] bg-white shadow-sm ring-1 ring-slate-100">
                            <div className="shrink-0 flex flex-col gap-3 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                                <div>
                                    <h2 className="text-lg font-bold leading-6 text-slate-900">{selectedConfig.label}</h2>
                                    <p className="mt-0.5 text-sm text-slate-500">{selectedConfig.description}</p>
                                </div>
                                <div className="rounded-full bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-600">
                                    {totalItems} {'b\u1ea3n ghi \u0111\u00e3 x\u00f3a'}
                                </div>
                            </div>

                            {error && (
                                <div className="mx-5 mt-4 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
                                    {error}
                                </div>
                            )}

                            {isLoading || records.length > 0 ? (
                                <div className="min-h-0 flex-1 overflow-auto">
                                    <table className="min-w-full divide-y divide-slate-100">
                                        <thead className="sticky top-0 z-10 bg-slate-50/95 backdrop-blur">
                                            <tr>
                                                <th className="px-5 py-2.5 text-left text-xs font-bold uppercase tracking-wide text-slate-400">{'T\u00ean'}</th>
                                                <th className="px-5 py-2.5 text-left text-xs font-bold uppercase tracking-wide text-slate-400">ID</th>
                                                <th className="px-5 py-2.5 text-left text-xs font-bold uppercase tracking-wide text-slate-400">{'Th\u1eddi \u0111i\u1ec3m x\u00f3a'}</th>
                                                <th className="px-5 py-2.5 text-right text-xs font-bold uppercase tracking-wide text-slate-400">{'H\u00e0nh \u0111\u1ed9ng'}</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-100">
                                            {isLoading ? (
                                                Array.from({ length: 5 }).map((_, index) => (
                                                    <tr key={index}>
                                                        <td className="px-5 py-3"><div className="h-4 w-48 animate-pulse rounded bg-slate-100" /></td>
                                                        <td className="px-5 py-3"><div className="h-4 w-56 animate-pulse rounded bg-slate-100" /></td>
                                                        <td className="px-5 py-3"><div className="h-4 w-32 animate-pulse rounded bg-slate-100" /></td>
                                                        <td className="px-5 py-3 text-right"><div className="ml-auto h-8 w-24 animate-pulse rounded-full bg-slate-100" /></td>
                                                    </tr>
                                                ))
                                            ) : (
                                                records.map((record) => (
                                                    <tr key={record.id} className="hover:bg-slate-50/60">
                                                        <td className="px-5 py-3">
                                                            <div className="max-w-[280px] truncate text-sm font-semibold text-slate-800" title={record.name}>
                                                                {record.name}
                                                            </div>
                                                            <div className="mt-1 text-xs text-slate-400">{getResourceDisplayName(record.type)}</div>
                                                        </td>
                                                        <td className="px-5 py-3">
                                                            <code className="rounded bg-slate-50 px-2 py-1 text-xs text-slate-500">{record.id}</code>
                                                        </td>
                                                        <td className="px-5 py-3 text-sm text-slate-500">{formatDate(record.deleted_at)}</td>
                                                        <td className="px-5 py-3 text-right">
                                                            <button
                                                                onClick={() => void handleRestore(record)}
                                                                disabled={!!restoringId}
                                                                className="inline-flex items-center justify-center gap-2 rounded-full bg-[#b75b00] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#9d4300] disabled:cursor-not-allowed disabled:opacity-60"
                                                            >
                                                                <AppIcon name="restore" className={`h-4 w-4 ${restoringId === record.id ? 'animate-spin' : ''}`} />
                                                                {'Kh\u00f4i ph\u1ee5c'}
                                                            </button>
                                                        </td>
                                                    </tr>
                                                ))
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            ) : (
                                <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
                                    <table className="min-w-full divide-y divide-slate-100">
                                        <thead className="bg-slate-50/95">
                                            <tr>
                                                <th className="px-5 py-2.5 text-left text-xs font-bold uppercase tracking-wide text-slate-400">{'T\u00ean'}</th>
                                                <th className="px-5 py-2.5 text-left text-xs font-bold uppercase tracking-wide text-slate-400">ID</th>
                                                <th className="px-5 py-2.5 text-left text-xs font-bold uppercase tracking-wide text-slate-400">{'Th\u1eddi \u0111i\u1ec3m x\u00f3a'}</th>
                                                <th className="px-5 py-2.5 text-right text-xs font-bold uppercase tracking-wide text-slate-400">{'H\u00e0nh \u0111\u1ed9ng'}</th>
                                            </tr>
                                        </thead>
                                    </table>
                                    <div className="flex min-h-0 flex-1 items-center justify-center px-5 py-6 text-center">
                                        <div>
                                            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-50">
                                                <AppIcon name="inbox" className="h-6 w-6 text-slate-300" />
                                            </div>
                                            <p className="text-sm font-semibold text-slate-700">{'Kh\u00f4ng c\u00f3 b\u1ea3n ghi \u0111\u00e3 x\u00f3a'}</p>
                                            <p className="mt-1 text-xs text-slate-400">{'Lo\u1ea1i d\u1eef li\u1ec7u n\u00e0y kh\u00f4ng c\u00f3 g\u00ec \u0111\u1ec3 kh\u00f4i ph\u1ee5c.'}</p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div className="shrink-0 flex flex-col gap-3 border-t border-slate-100 px-5 py-3.5 sm:flex-row sm:items-center sm:justify-between">
                                <p className="text-sm text-slate-500">Trang {page} / {totalPages}</p>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => setPage((current) => Math.max(1, current - 1))}
                                        disabled={page <= 1 || isLoading}
                                        className="rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
                                    >
                                        {'Tr\u01b0\u1edbc'}
                                    </button>
                                    <button
                                        onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                                        disabled={page >= totalPages || isLoading}
                                        className="rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
                                    >
                                        Sau
                                    </button>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    )
}
