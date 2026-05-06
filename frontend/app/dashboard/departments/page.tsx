'use client'

/**
 * Departments Management Page
 * RBAC: Admin + Manager can access. Regular users see access denied.
 * - Admin: Full CRUD (create, edit, delete departments)
 * - Manager: View-only (can see department tree and details)
 */

import React, { useState } from 'react'
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

export default function DepartmentsPage() {
    const { isAdmin, isTruongPhong } = useRBAC()
    const { user } = useAuthContext()
    const router = useRouter()

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
        refetch,
    } = useDepartments()

    // RBAC Guard - Only admin and manager can access
    if (!isAdmin() && !isTruongPhong()) {
        return (
            <AccessDeniedPage
                title="Truy cập bị hạn chế"
                message="Bạn cần quyền Quản trị viên hoặc Trưởng phòng để truy cập trang Quản lý Phòng ban."
                icon="🏢"
                showBackButton={true}
                onGoBack={() => router.push('/dashboard')}
            />
        )
    }

    // Determine if user can edit (only admin can add/edit/delete departments)
    const canEdit = isAdmin()

    // Auto-select department when data loads
    React.useEffect(() => {
        if (!Array.isArray(departments) || departments.length === 0 || selectedDepartmentId) return

        // Managers auto-select their own department only
        if (isTruongPhong()) {
            const myDept = departments.find((d) => d.id === user?.department_id)
            if (myDept) {
                setSelectedDepartmentId(myDept.id)
            } else {
                // If manager isn't mapped to any department in list, don't auto-select a different one
                setSelectedDepartmentId(null)
            }
            return
        }

        // Admins and others: default to first
        setSelectedDepartmentId(departments[0].id)
    }, [departments, selectedDepartmentId, isTruongPhong, user])

    const selectedDepartment = (Array.isArray(departments) ? departments : []).find((d) => d.id === selectedDepartmentId) ?? null

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
            {/* Main Content Area */}
            <main className="p-6 max-w-7xl mx-auto">
                {/* Header Section */}
                <DepartmentHeader
                    title="Quản lý Phòng ban"
                    subtitle="Kiến trúc hóa sơ đồ tổ chức và quản trị luồng tri thức giữa các đơn vị nghiệp vụ."
                    viewMode={viewMode}
                    onViewModeChange={setViewMode}
                />

                {/* Manager notice badge */}
                {!canEdit && (
                    <div
                        className="mb-4 px-4 py-2 rounded-lg text-sm flex items-center gap-2"
                        style={{
                            backgroundColor: '#fff3e0',
                            color: '#e65100',
                            border: '1px solid #ffe0b2',
                        }}
                    >
                        <span>ℹ️</span>
                        <span>Bạn đang xem với quyền <strong>Trưởng phòng</strong> — chỉ có thể xem, không thể chỉnh sửa cấu trúc phòng ban.</span>
                    </div>
                )}

                {viewMode === 'tree' ? (
                    <div className="grid grid-cols-12 gap-6 relative">
                        {/* Org Tree Section */}
                        <DepartmentTree
                            departments={departments}
                            selectedId={selectedDepartmentId}
                            onSelect={setSelectedDepartmentId}
                        />

                        {/* Right Sidebar Details */}
                        <div className="col-span-12 lg:col-span-5 flex flex-col gap-4">
                            {isAdmin() || (isTruongPhong() && selectedDepartment?.id === user?.department_id) ? (
                                <DepartmentSidebar
                                    department={selectedDepartment}
                                    onEdit={canEdit ? () => setIsEditDialogOpen(true) : undefined}
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
                    <>
                        {/* List View */}
                        <DepartmentList
                            departments={departments}
                            onAdd={canEdit ? () => setIsDialogOpen(true) : undefined}
                            onEdit={canEdit ? (dept) => {
                                setSelectedDepartmentId(dept.id)
                                setIsEditDialogOpen(true)
                            } : undefined}
                            onExport={handleExport}
                        />
                    </>
                )}

                {/* Add Department Dialog - Admin only */}
                {canEdit && (
                    <AddDepartmentDialog
                        isOpen={isDialogOpen}
                        onClose={() => setIsDialogOpen(false)}
                        onSubmit={handleAddDepartment}
                        isLoading={isSubmitting}
                        departments={departments}
                    />
                )}

                {/* Edit Department Dialog - Admin only */}
                {canEdit && (
                    <EditDepartmentDialog
                        isOpen={isEditDialogOpen}
                        onClose={() => setIsEditDialogOpen(false)}
                        onSubmit={handleEditDepartment}
                        isLoading={isSubmitting}
                        department={selectedDepartment}
                    />
                )}
            </main>

            {/* Floating Action Button - Admin only */}
            {canEdit && (
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
