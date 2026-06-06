'use client'

import React from 'react'
import { AlertCircle, Check, Loader2, Search, UserPlus, X } from 'lucide-react'
import type { Department } from '@/types/api'
import { getAllUsers, type User } from '@/services/users'
import type { AddDepartmentUsersResult } from '@/services/department'

interface AddDepartmentUsersDialogProps {
    isOpen: boolean
    department: Department | null
    onClose: () => void
    onSubmit: (accountIds: string[]) => Promise<AddDepartmentUsersResult>
    isLoading?: boolean
}

const MAX_SELECTED_USERS = 100

function getInitials(user: User) {
    const source = user.full_name || user.username || user.email
    return source
        .split(' ')
        .filter(Boolean)
        .map((part) => part[0])
        .join('')
        .substring(0, 2)
        .toUpperCase()
}

function getAccountId(user: User) {
    return user.account_id || user.id
}

export function AddDepartmentUsersDialog({
    isOpen,
    department,
    onClose,
    onSubmit,
    isLoading = false,
}: AddDepartmentUsersDialogProps) {
    const [users, setUsers] = React.useState<User[]>([])
    const [search, setSearch] = React.useState('')
    const [selectedIds, setSelectedIds] = React.useState<Set<string>>(new Set())
    const [loadingUsers, setLoadingUsers] = React.useState(false)
    const [error, setError] = React.useState<string | null>(null)
    const [result, setResult] = React.useState<AddDepartmentUsersResult | null>(null)

    const loadUsers = React.useCallback(async () => {
        if (!isOpen) return

        try {
            setLoadingUsers(true)
            setError(null)
            const query = search.trim()
            const response = await getAllUsers(1, 200, query || undefined, undefined, undefined, true)
            setUsers(response.data)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Không thể tải danh sách người dùng'
            setError(message)
            setUsers([])
        } finally {
            setLoadingUsers(false)
        }
    }, [isOpen, search])

    React.useEffect(() => {
        if (!isOpen) {
            setUsers([])
            setSearch('')
            setSelectedIds(new Set())
            setError(null)
            setResult(null)
            return
        }

        const delay = search.trim() ? 250 : 0
        const timer = window.setTimeout(loadUsers, delay)
        return () => window.clearTimeout(timer)
    }, [isOpen, search, loadUsers])

    const availableUsers = React.useMemo(() => {
        if (!department) return []

        return users.filter((user) => {
            const accountId = getAccountId(user)
            if (!accountId) return false
            if (user.roles?.some((role) => role.code === 'admin')) return false
            return user.department_id !== department.id
        })
    }, [users, department])

    const toggleUser = (accountId: string) => {
        setError(null)
        setResult(null)
        setSelectedIds((current) => {
            const next = new Set(current)
            if (next.has(accountId)) {
                next.delete(accountId)
                return next
            }

            if (next.size >= MAX_SELECTED_USERS) {
                setError(`Chỉ được thêm tối đa ${MAX_SELECTED_USERS} người dùng trong một lần.`)
                return current
            }

            next.add(accountId)
            return next
        })
    }

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault()
        setError(null)
        setResult(null)

        const accountIds = Array.from(selectedIds)
        if (!department || accountIds.length === 0) {
            setError('Vui lòng chọn ít nhất một người dùng.')
            return
        }

        try {
            const response = await onSubmit(accountIds)
            setResult(response)

            const addedIds = new Set(response.added.map((item) => item.account_id))
            setSelectedIds((current) => {
                const next = new Set(current)
                addedIds.forEach((id) => next.delete(id))
                return next
            })

            if (response.error_count === 0) {
                onClose()
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Không thể thêm người dùng vào phòng ban'
            setError(message)
        }
    }

    if (!isOpen || !department) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white rounded-[24px] w-full max-w-[720px] shadow-2xl relative overflow-hidden animate-in zoom-in-95 duration-200">
                <button
                    type="button"
                    onClick={onClose}
                    className="absolute top-5 right-5 text-slate-400 hover:text-slate-700 transition-colors bg-slate-50 hover:bg-slate-100 p-1.5 rounded-full"
                    aria-label="Đóng"
                >
                    <X className="h-5 w-5" />
                </button>

                <form onSubmit={handleSubmit}>
                    <div className="p-7 border-b border-slate-100">
                        <div className="inline-flex items-center gap-2 px-3 py-1 bg-orange-100 text-[#9d4300] text-[10px] font-black uppercase tracking-widest rounded-full mb-3">
                            <UserPlus className="h-3.5 w-3.5" />
                            Thêm thành viên
                        </div>
                        <h2 className="text-xl font-extrabold text-[#0d1c2e] mb-1">
                            Thêm người dùng vào {department.name}
                        </h2>
                        <p className="text-[12px] text-slate-500 font-medium">
                            Chọn một hoặc nhiều account hiện có để chuyển vào phòng ban này.
                        </p>
                    </div>

                    <div className="p-7 space-y-4">
                        {(error || result) && (
                            <div className={`p-4 rounded-xl border ${error ? 'bg-red-50 border-red-200' : 'bg-emerald-50 border-emerald-200'}`}>
                                <div className="flex items-start gap-3">
                                    {error ? (
                                        <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
                                    ) : (
                                        <Check className="h-5 w-5 text-emerald-600 flex-shrink-0" />
                                    )}
                                    <div className="flex-1">
                                        {error ? (
                                            <p className="text-sm font-semibold text-red-800">{error}</p>
                                        ) : result ? (
                                            <>
                                                <p className="text-sm font-semibold text-emerald-800">
                                                    Đã thêm {result.added_count}/{result.requested_count} người dùng.
                                                </p>
                                                {result.errors.length > 0 && (
                                                    <div className="mt-2 space-y-1">
                                                        {result.errors.slice(0, 3).map((item) => (
                                                            <p key={`${item.account_id}-${item.index}`} className="text-xs text-orange-700">
                                                                {item.account_id}: {item.message}
                                                            </p>
                                                        ))}
                                                    </div>
                                                )}
                                            </>
                                        ) : null}
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="relative">
                            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                            <input
                                type="search"
                                value={search}
                                onChange={(event) => setSearch(event.target.value)}
                                className="w-full bg-[#f8f9ff] border border-slate-100 pl-11 pr-4 py-3 rounded-xl text-sm outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300]/20 transition-all font-medium text-slate-700 placeholder:text-slate-400"
                                placeholder="Tìm theo tên, email hoặc username..."
                            />
                        </div>

                        <div className="rounded-xl border border-slate-100 overflow-hidden">
                            <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-b border-slate-100">
                                <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">
                                    Danh sách người dùng
                                </span>
                                <span className="text-xs font-semibold text-[#9d4300]">
                                    Đã chọn {selectedIds.size}
                                </span>
                            </div>

                            <div className="max-h-[360px] overflow-y-auto">
                                {loadingUsers ? (
                                    <div className="py-12 flex items-center justify-center gap-2 text-sm text-slate-500">
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        Đang tải người dùng...
                                    </div>
                                ) : availableUsers.length > 0 ? (
                                    availableUsers.map((user) => {
                                        const accountId = getAccountId(user)
                                        const selected = selectedIds.has(accountId)

                                        return (
                                            <label
                                                key={accountId}
                                                className="flex items-center gap-3 px-4 py-3 border-b border-slate-50 last:border-b-0 hover:bg-slate-50 transition-colors cursor-pointer"
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={selected}
                                                    onChange={() => toggleUser(accountId)}
                                                    className="h-4 w-4 rounded border-slate-300 text-[#9d4300] focus:ring-[#9d4300]/30"
                                                />
                                                <div className="h-9 w-9 rounded-full bg-[#eff4ff] flex items-center justify-center text-xs font-bold text-blue-600 flex-shrink-0">
                                                    {getInitials(user) || '?'}
                                                </div>
                                                <div className="min-w-0 flex-1">
                                                    <p className="text-sm font-bold text-[#0d1c2e] truncate">
                                                        {user.full_name || user.username}
                                                    </p>
                                                    <p className="text-xs text-slate-500 truncate">
                                                        {user.email} {user.department_name ? `• ${user.department_name}` : '• Chưa có phòng ban'}
                                                    </p>
                                                </div>
                                                {selected && <Check className="h-4 w-4 text-[#9d4300] flex-shrink-0" />}
                                            </label>
                                        )
                                    })
                                ) : (
                                    <div className="py-12 text-center">
                                        <p className="text-sm font-semibold text-slate-600">Không có người dùng phù hợp</p>
                                        <p className="text-xs text-slate-400 mt-1">Người đã thuộc phòng ban này sẽ không hiển thị trong danh sách chọn.</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center justify-end gap-3 px-7 py-5 border-t border-slate-100">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-5 py-2.5 rounded-xl text-[13px] font-bold text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                        >
                            Hủy bỏ
                        </button>
                        <button
                            type="submit"
                            disabled={isLoading || selectedIds.size === 0}
                            className="px-5 py-2.5 bg-[#9d4300] hover:bg-[#833800] text-white rounded-xl text-[13px] font-bold flex items-center gap-2 transition-all shadow-lg shadow-orange-200 disabled:opacity-50 active:scale-95"
                        >
                            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
                            Thêm người dùng
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}
