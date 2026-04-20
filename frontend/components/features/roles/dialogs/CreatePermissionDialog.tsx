'use client'

import React from 'react'
import { CreatePermissionDialogLeftPanel } from './CreatePermissionDialogLeftPanel'
import { CreatePermissionDialogRightPanel } from './CreatePermissionDialogRightPanel'

interface CreatePermissionDialogProps {
    isOpen: boolean
    onClose: () => void
    onSubmit?: (data: {
        name: string
        description: string
        category: string
    }) => void
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
            <div className="fixed top-0 right-0 bottom-0 z-30 flex items-center justify-center p-4" style={{ left: '240px' }}>
                <div
                    className="bg-white rounded-2xl shadow-2xl flex flex-col lg:flex-row max-w-3xl w-full max-h-[90vh] overflow-hidden"
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
