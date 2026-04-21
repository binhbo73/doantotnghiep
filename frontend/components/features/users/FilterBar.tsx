'use client'

/**
 * Filter Bar Component
 * Provides search and filter options for users
 */

import React, { useState } from 'react'
import { Search, X, Filter } from 'lucide-react'

interface FilterBarProps {
    onSearch?: (query: string) => void
    onFilterChange?: (filters: FilterOptions) => void
    showAdvanced?: boolean
}

export interface FilterOptions {
    search?: string
    department?: string
    role?: string
    status?: 'all' | 'active' | 'inactive'
}

export function FilterBar({
    onSearch,
    onFilterChange,
    showAdvanced = true,
}: FilterBarProps) {
    const [searchQuery, setSearchQuery] = useState('')
    const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)
    const [filters, setFilters] = useState<FilterOptions>({
        status: 'all',
    })

    const handleSearch = (query: string) => {
        setSearchQuery(query)
        setFilters({ ...filters, search: query })
        onSearch?.(query)
    }

    const handleFilterChange = (newFilters: FilterOptions) => {
        setFilters(newFilters)
        onFilterChange?.(newFilters)
    }

    const clearFilters = () => {
        setSearchQuery('')
        setFilters({ status: 'all' })
        onSearch?.('')
        onFilterChange?.({ status: 'all' })
    }

    return (
        <div className="space-y-3">
            {/* Search Bar */}
            <div className="relative">
                <Search
                    size={16}
                    className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
                />
                <input
                    type="text"
                    placeholder="Tìm kiếm theo tên, email hoặc username..."
                    value={searchQuery}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 text-sm rounded-md border transition-all focus:outline-none focus:ring-2"
                    style={{
                        backgroundColor: '#ffffff',
                        borderColor: '#dce2f3',
                        color: '#0d1c2e',
                    }}
                    onFocus={(e) => {
                        e.currentTarget.style.borderColor = '#9d4300'
                        e.currentTarget.style.boxShadow = '0 0 0 3px rgba(157, 67, 0, 0.1)'
                    }}
                    onBlur={(e) => {
                        e.currentTarget.style.borderColor = '#dce2f3'
                        e.currentTarget.style.boxShadow = 'none'
                    }}
                />
                {searchQuery && (
                    <button
                        onClick={() => handleSearch('')}
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 p-1 hover:bg-gray-100 rounded"
                    >
                        <X size={18} />
                    </button>
                )}
            </div>

            {/* Advanced Filters Toggle */}
            {showAdvanced && (
                <div className="flex items-center justify-between">
                    <button
                        onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                        className="flex items-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium hover:bg-gray-100 transition-colors"
                        style={{ color: '#9d4300' }}
                    >
                        <Filter size={14} />
                        <span>Bộ lọc nâng cao</span>
                    </button>

                    {(searchQuery || filters.department || filters.role || filters.status !== 'all') && (
                        <button
                            onClick={clearFilters}
                            className="text-xs font-medium text-gray-500 hover:text-gray-700"
                        >
                            Xóa tất cả bộ lọc
                        </button>
                    )}
                </div>
            )}

            {/* Advanced Filters */}
            {showAdvancedFilters && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 rounded-lg border" style={{ backgroundColor: '#eff4ff', borderColor: '#dce2f3' }}>
                    {/* Status Filter */}
                    <div>
                        <label className="block text-sm font-medium mb-2" style={{ color: '#584237' }}>
                            Trạng thái
                        </label>
                        <select
                            value={filters.status}
                            onChange={(e) =>
                                handleFilterChange({
                                    ...filters,
                                    status: e.target.value as 'all' | 'active' | 'inactive',
                                })
                            }
                            className="w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-2"
                            style={{
                                backgroundColor: '#ffffff',
                                borderColor: '#dce2f3',
                                color: '#0d1c2e',
                            }}
                        >
                            <option value="all">Tất cả</option>
                            <option value="active">Hoạt động</option>
                            <option value="inactive">Không hoạt động</option>
                        </select>
                    </div>

                    {/* Department Filter */}
                    <div>
                        <label className="block text-sm font-medium mb-2" style={{ color: '#584237' }}>
                            Phòng ban
                        </label>
                        <input
                            type="text"
                            placeholder="Tìm phòng ban..."
                            onChange={(e) =>
                                handleFilterChange({
                                    ...filters,
                                    department: e.target.value || undefined,
                                })
                            }
                            className="w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-2"
                            style={{
                                backgroundColor: '#ffffff',
                                borderColor: '#dce2f3',
                                color: '#0d1c2e',
                            }}
                        />
                    </div>

                    {/* Role Filter */}
                    <div>
                        <label className="block text-sm font-medium mb-2" style={{ color: '#584237' }}>
                            Vai trò
                        </label>
                        <input
                            type="text"
                            placeholder="Tìm vai trò..."
                            onChange={(e) =>
                                handleFilterChange({
                                    ...filters,
                                    role: e.target.value || undefined,
                                })
                            }
                            className="w-full px-3 py-2 rounded-lg border focus:outline-none focus:ring-2"
                            style={{
                                backgroundColor: '#ffffff',
                                borderColor: '#dce2f3',
                                color: '#0d1c2e',
                            }}
                        />
                    </div>
                </div>
            )}
        </div>
    )
}

export default FilterBar
