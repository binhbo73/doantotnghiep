'use client'

/**
 * User Table Header Component
 * Displays table headers with sorting capability
 */

import React from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'

interface TableColumn {
    id: string
    label: string
    sortable?: boolean
    width?: string
}

interface UserTableHeaderProps {
    columns: TableColumn[]
    onSort?: (columnId: string) => void
    sortBy?: string
    sortOrder?: 'asc' | 'desc'
}

export function UserTableHeader({
    columns,
    onSort,
    sortBy,
    sortOrder = 'asc',
}: UserTableHeaderProps) {
    return (
        <thead className="border-b" style={{ borderColor: '#dce2f3' }}>
            <tr style={{ backgroundColor: '#eff4ff' }}>
                {columns.map((column) => (
                    <th
                        key={column.id}
                        className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wide cursor-pointer transition-colors"
                        style={{
                            color: '#584237',
                            width: column.width,
                            minWidth: column.width,
                            whiteSpace: 'nowrap',
                        }}
                        onClick={() => column.sortable && onSort?.(column.id)}
                    >
                        <div className="flex items-center gap-2">
                            {column.label && <span>{column.label}</span>}
                            {column.sortable && sortBy === column.id && (
                                <>
                                    {sortOrder === 'asc' ? (
                                        <ChevronUp size={14} />
                                    ) : (
                                        <ChevronDown size={14} />
                                    )}
                                </>
                            )}
                        </div>
                    </th>
                ))}
            </tr>
        </thead>
    )
}

export default UserTableHeader
