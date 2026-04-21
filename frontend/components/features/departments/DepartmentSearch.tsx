'use client'

import React from 'react'
import { Search, Filter, X } from 'lucide-react'

interface DepartmentSearchProps {
    onSearch: (query: string) => void
    onFilterChange: (filter: 'all' | 'active' | 'inactive') => void
    onSort: (sortBy: 'name' | 'members' | 'recent') => void
    searchQuery?: string
    currentFilter?: 'all' | 'active' | 'inactive'
}

export function DepartmentSearch({
    onSearch,
    onFilterChange,
    onSort,
    searchQuery = '',
    currentFilter = 'all',
}: DepartmentSearchProps) {
    const [localSearch, setLocalSearch] = React.useState(searchQuery)
    const [showFilters, setShowFilters] = React.useState(false)

    const handleSearch = (value: string) => {
        setLocalSearch(value)
        onSearch(value)
    }

    return (
        <div className="space-y-3 mb-6">
            {/* Search Bar */}
            <div className="flex gap-2">
                <div
                    className="flex-1 flex items-center gap-2 px-3 py-2 rounded-lg border"
                    style={{
                        backgroundColor: '#ffffff',
                        borderColor: '#e0e0e0',
                    }}
                >
                    <Search className="w-4 h-4" style={{ color: '#727785' }} />
                    <input
                        type="text"
                        placeholder="Tìm kiếm phòng ban..."
                        value={localSearch}
                        onChange={(e) => handleSearch(e.target.value)}
                        className="flex-1 text-sm outline-none bg-transparent"
                        style={{ color: '#151c27' }}
                    />
                    {localSearch && (
                        <button
                            onClick={() => handleSearch('')}
                            className="p-1 hover:bg-gray-100 rounded"
                        >
                            <X className="w-4 h-4" style={{ color: '#727785' }} />
                        </button>
                    )}
                </div>

                {/* Filter Button */}
                <button
                    onClick={() => setShowFilters(!showFilters)}
                    className="px-3 py-2 rounded-lg border flex items-center gap-2 transition-all"
                    style={{
                        backgroundColor: showFilters ? '#fff3e0' : '#ffffff',
                        borderColor: showFilters ? '#d35400' : '#e0e0e0',
                        color: showFilters ? '#d35400' : '#727785',
                    }}
                >
                    <Filter className="w-4 h-4" />
                    <span className="text-sm font-medium">Lọc</span>
                </button>
            </div>

            {/* Filter Panel */}
            {showFilters && (
                <div
                    className="p-4 rounded-lg space-y-3 border"
                    style={{
                        backgroundColor: '#fafafa',
                        borderColor: '#e0e0e0',
                    }}
                >
                    {/* Filter Options */}
                    <div className="space-y-2">
                        <label className="text-xs font-semibold" style={{ color: '#727785' }}>
                            Trạng thái
                        </label>
                        <div className="flex gap-2">
                            {(['all', 'active', 'inactive'] as const).map((filter) => (
                                <button
                                    key={filter}
                                    onClick={() => onFilterChange(filter)}
                                    className="px-3 py-2 text-xs rounded-lg font-medium transition-all"
                                    style={{
                                        backgroundColor: currentFilter === filter ? '#d35400' : '#ffffff',
                                        color: currentFilter === filter ? '#ffffff' : '#727785',
                                        border: `1px solid ${currentFilter === filter ? '#d35400' : '#e0e0e0'}`,
                                    }}
                                >
                                    {filter === 'all' && 'Tất cả'}
                                    {filter === 'active' && 'Hoạt động'}
                                    {filter === 'inactive' && 'Không hoạt động'}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Sort Options */}
                    <div className="space-y-2 pt-2 border-t border-gray-200">
                        <label className="text-xs font-semibold" style={{ color: '#727785' }}>
                            Sắp xếp theo
                        </label>
                        <div className="flex gap-2">
                            {(['name', 'members', 'recent'] as const).map((sort) => (
                                <button
                                    key={sort}
                                    onClick={() => onSort(sort)}
                                    className="px-3 py-2 text-xs rounded-lg hover:bg-gray-200 transition-all"
                                    style={{
                                        color: '#727785',
                                    }}
                                >
                                    {sort === 'name' && 'Tên'}
                                    {sort === 'members' && 'Thành viên'}
                                    {sort === 'recent' && 'Gần đây'}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
