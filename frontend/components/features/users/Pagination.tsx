'use client'

/**
 * Pagination Component
 * Handles navigation between pages
 */

import React from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface PaginationProps {
    currentPage: number
    totalPages: number
    totalItems: number
    pageSize: number
    onPageChange: (page: number) => void
    onPageSizeChange?: (pageSize: number) => void
}

export function Pagination({
    currentPage,
    totalPages,
    totalItems,
    pageSize,
    onPageChange,
    onPageSizeChange,
}: PaginationProps) {
    const startItem = (currentPage - 1) * pageSize + 1
    const endItem = Math.min(currentPage * pageSize, totalItems)

    const getPageNumbers = () => {
        const pages = []
        const maxPages = 5
        const halfMax = Math.floor(maxPages / 2)

        let start = Math.max(1, currentPage - halfMax)
        let end = Math.min(totalPages, start + maxPages - 1)

        if (end - start < maxPages - 1) {
            start = Math.max(1, end - maxPages + 1)
        }

        for (let i = start; i <= end; i++) {
            pages.push(i)
        }

        return pages
    }

    return (
        <div className="flex items-center justify-between mt-6 px-4 py-4 rounded-lg border" style={{ backgroundColor: '#eff4ff', borderColor: '#dce2f3' }}>
            <div className="flex items-center gap-4">
                <div className="text-sm" style={{ color: '#584237' }}>
                    Hiển thị <strong>{startItem}</strong> đến <strong>{endItem}</strong> trong{' '}
                    <strong>{totalItems}</strong> kết quả
                </div>

                {onPageSizeChange && (
                    <select
                        value={pageSize}
                        onChange={(e) => onPageSizeChange(Number(e.target.value))}
                        className="px-3 py-1 rounded border text-sm"
                        style={{
                            backgroundColor: '#ffffff',
                            borderColor: '#dce2f3',
                            color: '#0d1c2e',
                        }}
                    >
                        <option value={10}>10 / trang</option>
                        <option value={25}>25 / trang</option>
                        <option value={50}>50 / trang</option>
                        <option value={100}>100 / trang</option>
                    </select>
                )}
            </div>

            <div className="flex items-center gap-2">
                {/* Previous Button */}
                <button
                    onClick={() => onPageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="p-2 rounded-lg border disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 transition-colors"
                    style={{ borderColor: '#dce2f3' }}
                    title="Trang trước"
                >
                    <ChevronLeft size={18} />
                </button>

                {/* Page Numbers */}
                <div className="flex items-center gap-1">
                    {getPageNumbers().map((page) => (
                        <button
                            key={page}
                            onClick={() => onPageChange(page)}
                            className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${currentPage === page
                                    ? 'text-white'
                                    : 'hover:bg-gray-100 border'
                                }`}
                            style={{
                                backgroundColor:
                                    currentPage === page ? '#9d4300' : 'transparent',
                                borderColor: currentPage === page ? '#9d4300' : '#dce2f3',
                                color: currentPage === page ? '#ffffff' : '#0d1c2e',
                            }}
                        >
                            {page}
                        </button>
                    ))}
                </div>

                {/* Next Button */}
                <button
                    onClick={() => onPageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="p-2 rounded-lg border disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 transition-colors"
                    style={{ borderColor: '#dce2f3' }}
                    title="Trang sau"
                >
                    <ChevronRight size={18} />
                </button>
            </div>
        </div>
    )
}

export default Pagination
