'use client'

import React from 'react'
import { CreateRoleDialogLeftPanel } from './CreateRoleDialogLeftPanel'
import { CreateRoleDialogRightPanel } from './CreateRoleDialogRightPanel'

interface Permission {
    id: string
    name: string
    checked: boolean
}

interface CreateRoleDialogProps {
    isOpen: boolean
    isEdit?: boolean
    initialData?: {
        code: string
        displayName: string
        description: string
        permissions: Permission[]
    }
    onClose: () => void
    onSubmit?: (data: {
        code: string
        displayName: string
        description: string
        permissions: Permission[]
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
            <div className="fixed top-0 right-0 bottom-0 z-30 flex items-center justify-center p-2" style={{ left: '240px' }}>
                <div
                    className="bg-white rounded-2xl shadow-2xl flex flex-col lg:flex-row w-full h-[96vh] max-w-[1800px] overflow-hidden"
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
