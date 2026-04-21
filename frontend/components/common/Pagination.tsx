/**
 * Pagination Component
 * Handles page navigation with configurable page size
 */

import React from 'react';

interface PaginationProps {
    currentPage: number;
    totalPages: number;
    pageSize: number;
    onPageChange: (page: number) => void;
    onPageSizeChange: (pageSize: number) => void;
}

export default function Pagination({
    currentPage,
    totalPages,
    pageSize,
    onPageChange,
    onPageSizeChange,
}: PaginationProps) {
    const pageSizeOptions = [5, 10, 20, 50];

    const handlePrevious = () => {
        if (currentPage > 1) {
            onPageChange(currentPage - 1);
        }
    };

    const handleNext = () => {
        if (currentPage < totalPages) {
            onPageChange(currentPage + 1);
        }
    };

    return (
        <div className="flex items-center justify-between border-t border-outline-variant pt-4">
            {/* Left: Page Size */}
            <div className="flex items-center gap-3">
                <label className="text-label-md text-on-surface-variant">Hiển thị</label>
                <select
                    value={pageSize}
                    onChange={(e) => {
                        onPageSizeChange(parseInt(e.target.value));
                        onPageChange(1); // Reset to page 1
                    }}
                    className="px-3 py-2 bg-surface-container-lowest border border-outline-variant rounded-lg text-body-md"
                >
                    {pageSizeOptions.map((size) => (
                        <option key={size} value={size}>
                            {size} trên trang
                        </option>
                    ))}
                </select>
            </div>

            {/* Center: Page Info */}
            <div className="text-label-md text-on-surface-variant">
                Trang {currentPage} / {totalPages}
            </div>

            {/* Right: Navigation */}
            <div className="flex items-center gap-2">
                <button
                    onClick={handlePrevious}
                    disabled={currentPage === 1}
                    className="px-4 py-2 bg-surface-container-low text-on-surface rounded-lg hover:bg-surface-container transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                    ← Trước
                </button>

                {/* Page Numbers */}
                <div className="flex gap-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        let pageNum: number;
                        if (totalPages <= 5) {
                            pageNum = i + 1;
                        } else if (currentPage <= 3) {
                            pageNum = i + 1;
                        } else if (currentPage >= totalPages - 2) {
                            pageNum = totalPages - 4 + i;
                        } else {
                            pageNum = currentPage - 2 + i;
                        }

                        return (
                            <button
                                key={pageNum}
                                onClick={() => onPageChange(pageNum)}
                                className={`w-10 h-10 rounded-lg font-medium transition-colors ${pageNum === currentPage
                                        ? 'bg-primary text-on-primary'
                                        : 'bg-surface-container-low text-on-surface hover:bg-surface-container'
                                    }`}
                            >
                                {pageNum}
                            </button>
                        );
                    })}
                </div>

                <button
                    onClick={handleNext}
                    disabled={currentPage === totalPages}
                    className="px-4 py-2 bg-surface-container-low text-on-surface rounded-lg hover:bg-surface-container transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                    Sau →
                </button>
            </div>
        </div>
    );
}
