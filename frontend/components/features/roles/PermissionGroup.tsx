'use client'

import React from 'react'
import { IamPermission } from '@/types/api'

interface Permission extends IamPermission {
    checked: boolean
}

interface PermissionGroupProps {
    group: {
        id: string
        name: string
        icon: string
        permissions: Permission[]
    }
    onToggle: (permissionId: string) => void
}

export function PermissionGroup({ group, onToggle }: PermissionGroupProps) {
    return (
        <div
            className="p-4 rounded-lg border flex flex-col h-full"
            style={{
                backgroundColor: '#ffffff',
                borderColor: '#dce2f3',
                minHeight: '300px',
            }}
        >
            {/* Group Header */}
            <h3 className="font-bold text-sm mb-4 flex items-center gap-2 pb-3 border-b" style={{ color: '#151c27', borderColor: '#e0e4f0' }}>
                <span className="text-xl">{group.icon}</span>
                <span className="flex-1">{group.name}</span>
            </h3>

            {/* Permissions List */}
            <div className="space-y-0 flex-1 overflow-y-auto">
                {group.permissions.map((permission) => (
                    <label
                        key={permission.id}
                        className="flex items-start gap-3 p-3 rounded cursor-pointer transition border border-transparent hover:border-blue-100 hover:bg-blue-50"
                        style={{
                            minHeight: '60px',
                            backgroundColor: permission.checked ? '#f0f7ff' : 'transparent',
                        }}
                    >
                        <input
                            type="checkbox"
                            checked={permission.checked}
                            onChange={() => onToggle(permission.id)}
                            className="w-4 h-4 rounded flex-shrink-0 mt-0.5"
                            style={{
                                accentColor: '#0058be',
                            }}
                        />
                        <div className="flex-1 min-w-0">
                            <span
                                className="text-xs block font-medium"
                                style={{
                                    color: permission.checked ? '#0058be' : '#151c27',
                                }}
                            >
                                {permission.code}
                            </span>
                            {permission.description && (
                                <span
                                    className="text-xs block mt-0.5"
                                    style={{ color: '#727785' }}
                                >
                                    {permission.description}
                                </span>
                            )}
                        </div>
                        {permission.checked && (
                            <span className="text-sm flex-shrink-0 font-bold" style={{ color: '#0058be' }}>✓</span>
                        )}
                    </label>
                ))}
            </div>
        </div>
    )
}
