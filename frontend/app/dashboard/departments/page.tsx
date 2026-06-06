'use client'

/**
 * Departments Management Page
 * RBAC:
 * - department_manage: create/delete departments and access the full department tree
 * - department_update: edit departments within the backend-approved scope
 * - department_read: view departments within the backend-approved scope
 */

import React, { useEffect, useState } from 'react'
import { toast } from 'sonner'
import {
    DepartmentHeader,
    DepartmentTree,
    DepartmentSidebar,
    AddDepartmentDialog,
    AddDepartmentUsersDialog,
    EditDepartmentDialog,
    DepartmentList,
} from '@/components/features/departments'
import { useDepartments } from '@/hooks/useDepartments'
import { useRBAC } from '@/hooks/useRBAC'
import { useAuthContext } from '@/context'
import { AccessDeniedPage } from '@/components/common/AccessDeniedPage'
import { useRouter } from 'next/navigation'
import type { Department } from '@/types/api'
import { addUsersToDepartment } from '@/services/department'
import { DeleteConfirmDialog } from '@/components/common/DeleteConfirmDialog'
import { getSafeDeleteBlockers } from '@/lib/safeDelete'

function DepartmentManagementContent() {
    const { hasPermission, hasAnyPermission } = useRBAC()
    const { user } = useAuthContext()
    const canReadDepartments = hasPermission('department_read')
    const canUpdateDepartments = hasAnyPermission(['department_update', 'department_manage'])
    const canManageDepartments = hasPermission('department_manage')
    const canCreateDepartments = hasAnyPermission(['department_create', 'department_manage'])
    const canAddUsersToDepartment = hasPermission('user_read') && hasPermission('user_update') && canUpdateDepartments

    const [isDialogOpen, setIsDialogOpen] = useState(false)
    const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
    const [isAddUsersDialogOpen, setIsAddUsersDialogOpen] = useState(false)
    const [selectedDepartmentId, setSelectedDepartmentId] = useState<string | null>(null)
    const [viewMode, setViewMode] = useState<'tree' | 'list'>('tree')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [departmentToDelete, setDepartmentToDelete] = useState<Department | null>(null)
    const [isDeletingDepartment, setIsDeletingDepartment] = useState(false)
    const [departmentDeleteBlockers, setDepartmentDeleteBlockers] = useState<string[]>([])
    const [detailRefreshKey, setDetailRefreshKey] = useState(0)

    const {
        departments,
        isLoading,
        addDepartment,
        updateDepartment,
        deleteDepartment,
        refetch,
    } = useDepartments({ page_size: 100 }, canReadDepartments)

    // Determine if user has full management rights
    const isFullManager = canManageDepartments

    const displayedDepartments: Department[] = canReadDepartments ? departments : []

    // Auto-select department when data loads
    useEffect(() => {
        if (!Array.isArray(displayedDepartments) || displayedDepartments.length === 0 || selectedDepartmentId) return

        if (canUpdateDepartments) {
            const myManaged = displayedDepartments.find((d) => d.id === user?.department_id) || displayedDepartments[0]
            setSelectedDepartmentId(myManaged?.id ?? null)
            return
        }

        setSelectedDepartmentId(displayedDepartments[0].id)
    }, [displayedDepartments, selectedDepartmentId, canUpdateDepartments, user?.department_id])

    const selectedDepartment: Department | null = (Array.isArray(displayedDepartments) ? displayedDepartments : []).find((d) => d.id === selectedDepartmentId) ?? null
    const canEditSelectedDepartment: boolean = !!selectedDepartment && canUpdateDepartments

    const handleSelectDepartment = (deptId: string) => {
        if (!canReadDepartments) {
            return
        }
        setSelectedDepartmentId(deptId)
    }

    const handleAddDepartment = async (data: {
        name: string
        description: string
        parent_id: string | null
        manager_id: string | null
    }) => {
        try {
            setIsSubmitting(true)
            await addDepartment({
                name: data.name,
                description: data.description || undefined,
                parent_id: data.parent_id,
                manager_id: data.manager_id,
            })
            setIsDialogOpen(false)
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Không thể tạo phòng ban'
            console.error('Failed to add department:', err)
            throw new Error(errorMessage)
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleEditDepartment = async (data: {
        name: string
        description: string
        manager_id: string | null
    }) => {
        if (!selectedDepartmentId) return
        try {
            setIsSubmitting(true)
            await updateDepartment(selectedDepartmentId, {
                name: data.name,
                description: data.description || undefined,
                manager_id: data.manager_id,
            })
            setIsEditDialogOpen(false)
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Không thể cập nhật phòng ban'
            console.error('Failed to update department:', err)
            throw new Error(errorMessage)
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleAddUsersToDepartment = async (accountIds: string[]) => {
        if (!selectedDepartmentId) {
            throw new Error('Vui lòng chọn phòng ban trước khi thêm người dùng')
        }

        try {
            setIsSubmitting(true)
            const result = await addUsersToDepartment(selectedDepartmentId, {
                account_ids: accountIds,
                reason: 'Added from departments dashboard',
            })
            await refetch({ page_size: 100 })
            setDetailRefreshKey((current) => current + 1)
            return result
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Không thể thêm người dùng vào phòng ban'
            console.error('Failed to add users to department:', err)
            throw new Error(errorMessage)
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleDeleteDepartment = async () => {
        if (!departmentToDelete || !canManageDepartments) return

        const deletedDepartment = departmentToDelete
        setIsDeletingDepartment(true)
        try {
            await deleteDepartment(deletedDepartment.id)

            if (selectedDepartmentId === deletedDepartment.id) {
                setSelectedDepartmentId(null)
            }

            setDepartmentToDelete(null)
            setDepartmentDeleteBlockers([])
            toast.success(`Đã xóa phòng ban "${deletedDepartment.name}"`)
        } catch (err) {
            const blockers = getSafeDeleteBlockers(err)
            if (blockers) {
                const items = [
                    blockers.users ? `${blockers.users} nhân viên trực tiếp` : null,
                    blockers.child_departments ? `${blockers.child_departments} phòng ban con` : null,
                    blockers.folders ? `${blockers.folders} thư mục` : null,
                    blockers.documents ? `${blockers.documents} tài liệu` : null,
                ].filter((item): item is string => Boolean(item))

                setDepartmentDeleteBlockers(
                    items.length > 0
                        ? items
                        : ['Phòng ban vẫn còn dữ liệu liên quan']
                )
                return
            }

            const message = err instanceof Error
                ? err.message
                : 'Không thể xóa phòng ban'
            toast.error(message)
        } finally {
            setIsDeletingDepartment(false)
        }
    }

    const handleExport = () => {
        console.log('Exporting departments...')
    }

    if (isLoading) {
        return (
            <div className="min-h-screen bg-[#f8f9ff] flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-10 h-10 border-4 border-[#9d4300]/20 border-t-[#9d4300] rounded-full animate-spin" />
                    <p className="text-sm text-slate-500 font-medium">Đang tải dữ liệu phòng ban...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-[#f8f9ff]">
            <main className="p-6 max-w-7xl mx-auto">
                <DepartmentHeader
                    title="Quản lý Phòng ban"
                    subtitle="Kiến trúc hóa sơ đồ tổ chức và quản trị luồng tri thức giữa các đơn vị nghiệp vụ."
                    viewMode={viewMode}
                    onViewModeChange={setViewMode}
                />

                {!isFullManager && (
                    <div
                        className="mb-4 px-4 py-2 rounded-lg text-sm flex items-center gap-2"
                        style={{
                            backgroundColor: '#fff3e0',
                            color: '#e65100',
                            border: '1px solid #ffe0b2',
                        }}
                    >
                        <span>ℹ️</span>
                        <span>
                            {!canUpdateDepartments
                                ? 'Bạn đang xem phòng ban của mình — chỉ có thể xem chi tiết cho phòng ban này.'
                                : 'Bạn đang xem với phạm vi quyền được cấp — chỉ có thể xem và chỉnh sửa trong cây phòng ban được phân quyền.'}
                        </span>
                    </div>
                )}

                {viewMode === 'tree' ? (
                    <div className="grid grid-cols-12 gap-6 relative">
                        <DepartmentTree
                            departments={displayedDepartments}
                            selectedId={selectedDepartmentId}
                            onSelect={handleSelectDepartment}
                            onEdit={(deptId) => {
                                setSelectedDepartmentId(deptId)
                                setIsEditDialogOpen(true)
                            }}
                            onDelete={canManageDepartments ? (deptId) => {
                                const department = displayedDepartments.find((item) => item.id === deptId)
                                if (department) {
                                    setDepartmentDeleteBlockers([])
                                    setDepartmentToDelete(department)
                                }
                            } : undefined}
                            deletingId={isDeletingDepartment ? departmentToDelete?.id : null}
                        />

                        <div className="col-span-12 lg:col-span-5 flex flex-col gap-4">
                            {selectedDepartment ? (
                                <DepartmentSidebar
                                    key={`${selectedDepartment.id}-${detailRefreshKey}`}
                                    department={selectedDepartment}
                                    onEdit={canEditSelectedDepartment ? () => setIsEditDialogOpen(true) : undefined}
                                    onAddUsers={canAddUsersToDepartment ? () => setIsAddUsersDialogOpen(true) : undefined}
                                />
                            ) : (
                                <div className="rounded-xl border border-slate-100 bg-white p-6">
                                    <div className="flex flex-col items-start gap-3">
                                        <h3 className="text-sm font-bold">Tổng quan Phòng ban</h3>
                                        <p className="text-xs text-slate-500">Bạn đang xem chế độ giới hạn. Chỉ các phòng ban nằm trong phạm vi được cấp quyền mới hiển thị chi tiết.</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <DepartmentList
                        departments={displayedDepartments}
                        onAdd={canCreateDepartments ? () => setIsDialogOpen(true) : undefined}
                        onEdit={(dept) => {
                            setSelectedDepartmentId(dept.id)
                            setIsEditDialogOpen(true)
                        }}
                        onDelete={canManageDepartments ? (department) => {
                            setDepartmentDeleteBlockers([])
                            setDepartmentToDelete(department)
                        } : undefined}
                        deletingId={isDeletingDepartment ? departmentToDelete?.id : null}
                        onExport={handleExport}
                    />
                )}

                {canCreateDepartments && (
                    <AddDepartmentDialog
                        isOpen={isDialogOpen}
                        onClose={() => setIsDialogOpen(false)}
                        onSubmit={handleAddDepartment}
                        isLoading={isSubmitting}
                        departments={departments}
                    />
                )}

                {canUpdateDepartments && (
                    <EditDepartmentDialog
                        isOpen={isEditDialogOpen}
                        onClose={() => setIsEditDialogOpen(false)}
                        onSubmit={handleEditDepartment}
                        isLoading={isSubmitting}
                        department={selectedDepartment}
                    />
                )}

                {canAddUsersToDepartment && (
                    <AddDepartmentUsersDialog
                        isOpen={isAddUsersDialogOpen}
                        department={selectedDepartment}
                        onClose={() => setIsAddUsersDialogOpen(false)}
                        onSubmit={handleAddUsersToDepartment}
                        isLoading={isSubmitting}
                    />
                )}

                <DeleteConfirmDialog
                    open={departmentToDelete !== null}
                    title={departmentDeleteBlockers.length > 0 ? 'Không thể xóa phòng ban' : 'Xóa phòng ban?'}
                    description={departmentDeleteBlockers.length > 0
                        ? 'Đây là cơ chế bảo vệ dữ liệu. Phòng ban chỉ được xóa sau khi đã chuyển hoặc xử lý hết dữ liệu liên quan.'
                        : 'Chỉ có thể xóa phòng ban rỗng. Hệ thống sẽ từ chối nếu còn nhân viên, phòng ban con, thư mục hoặc tài liệu.'}
                    resourceName={departmentToDelete?.name}
                    isDeleting={isDeletingDepartment}
                    blockedItems={departmentDeleteBlockers}
                    onOpenChange={(open) => {
                        if (!open) {
                            setDepartmentToDelete(null)
                            setDepartmentDeleteBlockers([])
                        }
                    }}
                    onConfirm={handleDeleteDepartment}
                />
            </main>

            {canCreateDepartments && (
                <button
                    onClick={() => setIsDialogOpen(true)}
                    className="fixed bottom-10 right-10 w-16 h-16 bg-[#9d4300] text-white rounded-full shadow-2xl flex items-center justify-center hover:scale-110 active:scale-95 transition-all group z-50 hover:shadow-[#f97316]/50"
                >
                    <span className="material-symbols-outlined text-3xl">add_business</span>
                    <span className="absolute right-full mr-4 bg-[#0d1c2e] text-white px-3 py-1 rounded-lg text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap shadow-lg">Thêm Phòng Ban</span>
                </button>
            )}
        </div>
    )
}

export default function DepartmentsPage() {
    const { hasPermission } = useRBAC()
    const { isLoading } = useAuthContext()
    const router = useRouter()
    const canReadDepartments = hasPermission('department_read')

    if (isLoading) {
        return (
            <div className="min-h-screen bg-[#f8f9ff] flex items-center justify-center">
                <div className="rounded-2xl bg-white p-8 shadow-sm border border-slate-200 text-center">
                    <p className="text-sm text-slate-600">Đang xác thực quyền truy cập...</p>
                </div>
            </div>
        )
    }

    if (!canReadDepartments) {
        return (
            <AccessDeniedPage
                title="Truy cập bị hạn chế"
                message="Bạn cần quyền department_read để truy cập trang Phòng ban."
                icon="🏢"
                showBackButton={true}
                onGoBack={() => router.push('/dashboard')}
            />
        )
    }

    return <DepartmentManagementContent />
}
