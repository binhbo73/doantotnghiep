'use client'

import React from 'react'
import { CreateRoleDialogLeftPanel } from './CreateRoleDialogLeftPanel'
import { CreateRoleDialogRightPanel } from './CreateRoleDialogRightPanel'
import { IamPermission } from '@/types/api'

interface RolePermission extends IamPermission {
    checked: boolean
}

interface CreateRoleDialogProps {
    isOpen: boolean
    isEdit?: boolean
    initialData?: {
        code: string
        displayName: string
        description: string
        permissions: RolePermission[]
    }
    onClose: () => void
    onSubmit?: (data: {
        code: string
        displayName: string
        description: string
        permissions: RolePermission[]
    }) => void
}

export function CreateRoleDialog({
    isOpen,
    isEdit = false,
    initialData,
    onClose,
    onSubmit,
}: CreateRoleDialogProps) {
    if (!isOpen) return null

    return (
        <>
            {/* Overlay - Only on main content area */}
            <div
                className="fixed top-0 right-0 bottom-0 bg-black/30 z-20 transition-opacity"
                style={{ left: '240px' }}
                onClick={onClose}
            />

            {/* Dialog Container - Only on main content area */}
            <div className="fixed top-0 right-0 bottom-0 z-30 flex items-center justify-center p-3" style={{ left: '240px' }}>
                <div
                    className="flex h-[82vh] max-h-[720px] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl lg:flex-row"
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Left Panel - Branding */}
                    <CreateRoleDialogLeftPanel isEdit={isEdit} />

                    {/* Right Panel - Form */}
                    <CreateRoleDialogRightPanel
                        isEdit={isEdit}
                        onClose={onClose}
                        onSubmit={onSubmit}
                        initialData={initialData}
                    />
                </div>
            </div>
        </>
    )
}
