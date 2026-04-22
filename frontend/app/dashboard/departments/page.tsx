'use client'

import React, { useState } from 'react'
import {
    DepartmentHeader,
    DepartmentTree,
    DepartmentSidebar,
    AddDepartmentDialog,
    DepartmentList,
} from '@/components/features/departments'
import { useDepartments } from '@/hooks/useDepartments'

export default function DepartmentsPage() {
    const [isDialogOpen, setIsDialogOpen] = useState(false)
    const [selectedDepartmentId, setSelectedDepartmentId] = useState<string | null>(null)
    const [viewMode, setViewMode] = useState<'tree' | 'list'>('tree')
    const [isSubmitting, setIsSubmitting] = useState(false)

    const {
        departments,
        isLoading,
        addDepartment,
        refetch,
    } = useDepartments()

    // Auto-select first department when data loads
    React.useEffect(() => {
        if (Array.isArray(departments) && departments.length > 0 && !selectedDepartmentId) {
            setSelectedDepartmentId(departments[0].id)
        }
    }, [departments])

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
            console.error('Failed to add department:', err)
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
                            <DepartmentSidebar
                                department={selectedDepartment}
                            />
                        </div>
                    </div>
                ) : (
                    <>
                        {/* List View */}
                        <DepartmentList
                            departments={departments}
                            onAdd={() => setIsDialogOpen(true)}
                            onExport={handleExport}
                        />
                    </>
                )}

                {/* Add Department Dialog */}
                <AddDepartmentDialog
                    isOpen={isDialogOpen}
                    onClose={() => setIsDialogOpen(false)}
                    onSubmit={handleAddDepartment}
                    isLoading={isSubmitting}
                    departments={departments}
                />
            </main>

            {/* Floating Action Button */}
            <button
                onClick={() => setIsDialogOpen(true)}
                className="fixed bottom-10 right-10 w-16 h-16 bg-[#9d4300] text-white rounded-full shadow-2xl flex items-center justify-center hover:scale-110 active:scale-95 transition-all group z-50 hover:shadow-[#f97316]/50"
            >
                <span className="material-symbols-outlined text-3xl">add_business</span>
                <span className="absolute right-full mr-4 bg-[#0d1c2e] text-white px-3 py-1 rounded-lg text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap shadow-lg">Thêm Phòng Ban</span>
            </button>
        </div>
    )
}
