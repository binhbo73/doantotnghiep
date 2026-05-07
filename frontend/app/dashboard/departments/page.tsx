'use client'

/**
 * Departments Management Page
 * RBAC: 
 * - Admin: Full CRUD (create, edit, delete departments) with access to all departments
 * - Manager (Trưởng phòng): View-only access, can see department tree and their own department details
 * - Regular users: Can see the tree view of their own department only
 */

import React, { useEffect, useState } from 'react'
import {
    DepartmentHeader,
    DepartmentTree,
    DepartmentSidebar,
    AddDepartmentDialog,
    EditDepartmentDialog,
    DepartmentList,
} from '@/components/features/departments'
import { useDepartments } from '@/hooks/useDepartments'
import { useRBAC } from '@/hooks/useRBAC'
import { useAuthContext } from '@/context'
import { AccessDeniedPage } from '@/components/common/AccessDeniedPage'
import { useRouter } from 'next/navigation'
import { canEditDepartment, filterVisibleDepartments } from '@/lib/departmentAccess'
import type { Department } from '@/types/api'

function DepartmentManagementContent() {
    const { isAdmin, isTruongPhong, isNhanVien } = useRBAC()
    const { user } = useAuthContext()
    const isAdminUser = isAdmin()
    const isManagerUser = isTruongPhong()
    const isRegularUser = isNhanVien() && !isManagerUser && !isAdminUser

    const [isDialogOpen, setIsDialogOpen] = useState(false)
    const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
    const [selectedDepartmentId, setSelectedDepartmentId] = useState<string | null>(null)
    const [viewMode, setViewMode] = useState<'tree' | 'list'>('tree')
    const [isSubmitting, setIsSubmitting] = useState(false)

    const {
        departments,
        isLoading,
        addDepartment,
        updateDepartment,
    } = useDepartments({ page_size: 100 })

    // Determine if user can edit/create/delete departments
    const canCreateOrDelete = isAdminUser

    const displayedDepartments: Department[] = filterVisibleDepartments({
        user,
        departments,
        isAdmin: isAdminUser,
        isTruongPhong: isManagerUser,
    })

    // Auto-select department when data loads
    useEffect(() => {
        if (!Array.isArray(displayedDepartments) || displayedDepartments.length === 0 || selectedDepartmentId) return

        if (isManagerUser) {
            const myManaged = displayedDepartments.find((d) => canEditDepartment({
                user,
                targetDeptId: d.id,
                departments: displayedDepartments,
                isAdmin: isAdminUser,
                isTruongPhong: isManagerUser,
            }))
            setSelectedDepartmentId(myManaged?.id ?? null)
            return
        }

        setSelectedDepartmentId(displayedDepartments[0].id)
    }, [displayedDepartments, selectedDepartmentId, isAdminUser, isManagerUser, user])

    const selectedDepartment: Department | null = (Array.isArray(displayedDepartments) ? displayedDepartments : []).find((d) => d.id === selectedDepartmentId) ?? null
    const canEditSelectedDepartment: boolean = selectedDepartment ? canEditDepartment({
        user,
        targetDeptId: selectedDepartment.id,
        departments: displayedDepartments,
        isAdmin: isAdminUser,
        isTruongPhong: isManagerUser,
    }) : false

    const handleSelectDepartment = (deptId: string) => {
        // Regular users can only select their own department
        if (isRegularUser && deptId !== user?.department_id) {
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

                {!canCreateOrDelete && (
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
                            {isRegularUser
                                ? 'Bạn đang xem phòng ban của mình — chỉ có thể xem chi tiết cho phòng ban này.'
                                : 'Bạn đang xem với quyền Trưởng phòng — chỉ có thể xem và chỉnh sửa trong phạm vi cây phòng ban được giao.'}
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
                        />

                        <div className="col-span-12 lg:col-span-5 flex flex-col gap-4">
                            {selectedDepartment ? (
                                <DepartmentSidebar
                                    department={selectedDepartment}
                                    onEdit={canEditSelectedDepartment ? () => setIsEditDialogOpen(true) : undefined}
                                />
                            ) : (
                                <div className="rounded-xl border border-slate-100 bg-white p-6">
                                    <div className="flex flex-col items-start gap-3">
                                        <h3 className="text-sm font-bold">Tổng quan Phòng ban</h3>
                                        <p className="text-xs text-slate-500">Bạn đang xem chế độ giới hạn. Trưởng phòng chỉ có thể xem chi tiết cho phòng ban của mình.</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <DepartmentList
                        departments={displayedDepartments}
                        onAdd={canCreateOrDelete ? () => setIsDialogOpen(true) : undefined}
                        onEdit={(dept) => {
                            setSelectedDepartmentId(dept.id)
                            setIsEditDialogOpen(true)
                        }}
                        onExport={handleExport}
                    />
                )}

                {canCreateOrDelete && (
                    <AddDepartmentDialog
                        isOpen={isDialogOpen}
                        onClose={() => setIsDialogOpen(false)}
                        onSubmit={handleAddDepartment}
                        isLoading={isSubmitting}
                        departments={departments}
                    />
                )}

                {canCreateOrDelete && (
                    <EditDepartmentDialog
                        isOpen={isEditDialogOpen}
                        onClose={() => setIsEditDialogOpen(false)}
                        onSubmit={handleEditDepartment}
                        isLoading={isSubmitting}
                        department={selectedDepartment}
                    />
                )}
            </main>

            {canCreateOrDelete && (
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
    const { isAdmin, isTruongPhong } = useRBAC()
    const { user, isLoading } = useAuthContext()
    const router = useRouter()
    const isAdminUser = isAdmin()
    const isManagerUser = isTruongPhong()

    if (isLoading) {
        return (
            <div className="min-h-screen bg-[#f8f9ff] flex items-center justify-center">
                <div className="rounded-2xl bg-white p-8 shadow-sm border border-slate-200 text-center">
                    <p className="text-sm text-slate-600">Đang xác thực quyền truy cập...</p>
                </div>
            </div>
        )
    }

    if (!isAdminUser && !isManagerUser && !user?.department_id) {
        return (
            <AccessDeniedPage
                title="Truy cập bị hạn chế"
                message="Bạn cần được gán cho một phòng ban để truy cập trang này."
                icon="🏢"
                showBackButton={true}
                onGoBack={() => router.push('/dashboard')}
            />
        )
    }

    return <DepartmentManagementContent />
}
