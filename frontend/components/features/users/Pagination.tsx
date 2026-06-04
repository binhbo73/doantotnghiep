'use client'

/**
 * Pagination Component
 * Handles navigation between pages.
 */

import React from 'react'
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'

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
    const safeTotalPages = Math.max(totalPages, 1)
    const safeCurrentPage = Math.min(Math.max(currentPage, 1), safeTotalPages)
    const startItem = totalItems === 0 ? 0 : (safeCurrentPage - 1) * pageSize + 1
    const endItem = Math.min(safeCurrentPage * pageSize, totalItems)
    const canGoPrevious = safeCurrentPage > 1
    const canGoNext = safeCurrentPage < safeTotalPages

    const handlePageChange = (page: number) => {
        const nextPage = Math.min(Math.max(page, 1), safeTotalPages)
        if (nextPage !== safeCurrentPage) {
            onPageChange(nextPage)
        }
    }

    const getPageNumbers = () => {
        const pages: number[] = []
        const maxPages = 5
        const halfMax = Math.floor(maxPages / 2)

        let start = Math.max(1, safeCurrentPage - halfMax)
        const end = Math.min(safeTotalPages, start + maxPages - 1)

        if (end - start < maxPages - 1) {
            start = Math.max(1, end - maxPages + 1)
        }

        for (let page = start; page <= end; page += 1) {
            pages.push(page)
        }

        return pages
    }

    const navButtonClass =
        'inline-flex h-9 w-9 items-center justify-center rounded-lg border border-[#dce2f3] bg-white text-slate-600 shadow-sm transition-colors hover:border-[#b9c6e6] hover:bg-slate-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-50 disabled:text-slate-300 disabled:shadow-none'

    return (
        <div className="mt-6 rounded-xl border border-[#dce2f3] bg-[#f3f6ff] px-4 py-3 shadow-sm">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex flex-wrap items-center gap-3">
                    <div className="rounded-lg bg-white px-3 py-2 text-sm text-slate-700 shadow-sm ring-1 ring-[#dce2f3]">
                        Hiển thị <strong className="text-slate-950">{startItem}</strong> đến{' '}
                        <strong className="text-slate-950">{endItem}</strong> trong{' '}
                        <strong className="text-slate-950">{totalItems}</strong> kết quả
                    </div>

                    {onPageSizeChange && (
                        <label className="flex items-center gap-2 text-sm text-slate-600">
                            <span className="hidden sm:inline">Mỗi trang</span>
                            <select
                                value={pageSize}
                                onChange={(e) => onPageSizeChange(Number(e.target.value))}
                                className="h-9 rounded-lg border border-[#dce2f3] bg-white px-3 text-sm font-medium text-slate-800 shadow-sm transition-colors focus:border-[#9d4300] focus:outline-none focus:ring-2 focus:ring-[#9d4300]/10"
                            >
                                <option value={10}>10</option>
                                <option value={25}>25</option>
                                <option value={50}>50</option>
                                <option value={100}>100</option>
                            </select>
                        </label>
                    )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    <span className="mr-1 rounded-lg bg-white px-3 py-2 text-sm font-medium text-slate-600 ring-1 ring-[#dce2f3]">
                        Trang {safeCurrentPage} / {safeTotalPages}
                    </span>

                    <button
                        type="button"
                        onClick={() => handlePageChange(1)}
                        disabled={!canGoPrevious}
                        className={navButtonClass}
                        title={canGoPrevious ? 'Trang đầu' : 'Đang ở trang đầu'}
                        aria-label="Trang đầu"
                    >
                        <ChevronsLeft size={17} />
                    </button>

                    <button
                        type="button"
                        onClick={() => handlePageChange(safeCurrentPage - 1)}
                        disabled={!canGoPrevious}
                        className={navButtonClass}
                        title={canGoPrevious ? 'Trang trước' : 'Không có trang trước'}
                        aria-label="Trang trước"
                    >
                        <ChevronLeft size={17} />
                    </button>

                    <div className="flex items-center gap-1">
                        {getPageNumbers().map((page) => (
                            <button
                                key={page}
                                type="button"
                                onClick={() => handlePageChange(page)}
                                aria-current={safeCurrentPage === page ? 'page' : undefined}
                                className={`h-9 min-w-9 rounded-lg px-3 text-sm font-semibold shadow-sm transition-colors ${
                                    safeCurrentPage === page
                                        ? 'bg-[#9d4300] text-white'
                                        : 'border border-[#dce2f3] bg-white text-slate-700 hover:border-[#b9c6e6] hover:bg-slate-50'
                                }`}
                            >
                                {page}
                            </button>
                        ))}
                    </div>

                    <button
                        type="button"
                        onClick={() => handlePageChange(safeCurrentPage + 1)}
                        disabled={!canGoNext}
                        className={navButtonClass}
                        title={canGoNext ? 'Trang sau' : 'Không có trang sau'}
                        aria-label="Trang sau"
                    >
                        <ChevronRight size={17} />
                    </button>

                    <button
                        type="button"
                        onClick={() => handlePageChange(safeTotalPages)}
                        disabled={!canGoNext}
                        className={navButtonClass}
                        title={canGoNext ? 'Trang cuối' : 'Đang ở trang cuối'}
                        aria-label="Trang cuối"
                    >
                        <ChevronsRight size={17} />
                    </button>
                </div>
            </div>
        </div>
    )
}

export default Pagination
