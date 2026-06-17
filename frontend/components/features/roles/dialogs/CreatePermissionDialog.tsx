'use client'

import React from 'react'
import { CreatePermissionDialogLeftPanel } from './CreatePermissionDialogLeftPanel'
import { CreatePermissionDialogRightPanel } from './CreatePermissionDialogRightPanel'

interface CreatePermissionDialogProps {
    isOpen: boolean
    onClose: () => void
    onSubmit?: (data: {
        code: string
        name: string
        description: string
        resource: string
        action: string
    }) => void | Promise<void>
}

export function CreatePermissionDialog({
    isOpen,
    onClose,
    onSubmit,
}: CreatePermissionDialogProps) {
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
                    className="flex w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl lg:flex-row"
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Left Panel - Branding */}
                    <CreatePermissionDialogLeftPanel />

                    {/* Right Panel - Form */}
                    <CreatePermissionDialogRightPanel
                        onClose={onClose}
                        onSubmit={onSubmit}
                    />
                </div>
            </div>
        </>
    )
}
