'use client'

/**
 * Action Menu Component
 * Dropdown menu for user row actions
 */

import React, { useState, useRef, useEffect } from 'react'
import { MoreVertical, Edit2, Trash2, Eye, Lock } from 'lucide-react'

interface ActionMenuProps {
    onEdit?: () => void
    onView?: () => void
    onDelete?: () => void
    onResetPassword?: () => void
    showEdit?: boolean
    showView?: boolean
    showDelete?: boolean
    showResetPassword?: boolean
}

export function ActionMenu({
    onEdit,
    onView,
    onDelete,
    onResetPassword,
    showEdit = true,
    showView = true,
    showDelete = true,
    showResetPassword = true,
}: ActionMenuProps) {
    const [isOpen, setIsOpen] = useState(false)
    const menuRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setIsOpen(false)
            }
        }

        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const handleMenuClick = (callback?: () => void) => {
        callback?.()
        setIsOpen(false)
    }

    return (
        <div className="relative" ref={menuRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                title="Thêm tùy chọn"
            >
                <MoreVertical size={18} />
            </button>

            {isOpen && (
                <div
                    className="absolute right-0 mt-1 w-48 bg-white rounded-lg shadow-lg z-50 border border-gray-200"
                    style={{ backgroundColor: '#ffffff', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)' }}
                >
                    {showView && (
                        <button
                            onClick={() => handleMenuClick(onView)}
                            className="w-full px-4 py-2 flex items-center gap-2 hover:bg-gray-50 text-left text-sm transition-colors"
                        >
                            <Eye size={16} />
                            <span>Xem chi tiết</span>
                        </button>
                    )}

                    {showEdit && (
                        <button
                            onClick={() => handleMenuClick(onEdit)}
                            className="w-full px-4 py-2 flex items-center gap-2 hover:bg-gray-50 text-left text-sm transition-colors"
                        >
                            <Edit2 size={16} />
                            <span>Chỉnh sửa</span>
                        </button>
                    )}

                    {showResetPassword && (
                        <button
                            onClick={() => handleMenuClick(onResetPassword)}
                            className="w-full px-4 py-2 flex items-center gap-2 hover:bg-gray-50 text-left text-sm transition-colors"
                        >
                            <Lock size={16} />
                            <span>Đặt lại mật khẩu</span>
                        </button>
                    )}

                    {showDelete && (
                        <button
                            onClick={() => handleMenuClick(onDelete)}
                            className="w-full px-4 py-2 flex items-center gap-2 hover:bg-red-50 text-left text-sm text-red-600 transition-colors border-t"
                        >
                            <Trash2 size={16} />
                            <span>Xóa</span>
                        </button>
                    )}
                </div>
            )}
        </div>
    )
}

export default ActionMenu
