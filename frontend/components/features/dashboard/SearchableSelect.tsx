/**
 * SearchableSelect Component - Dropdown với tìm kiếm
 * Giải quyết vấn đề dropdown quá dài
 */

'use client'

import React, { useState, useRef, useEffect } from 'react'

interface Option {
    id: string
    name: string
    [key: string]: any
}

interface SearchableSelectProps {
    options: Option[]
    value: string
    onChange: (value: string) => void
    placeholder?: string
    disabled?: boolean
    label?: string
    error?: string
}

export function SearchableSelect({
    options,
    value,
    onChange,
    placeholder = 'Chọn...',
    disabled = false,
    label,
    error,
}: SearchableSelectProps) {
    const [isOpen, setIsOpen] = useState(false)
    const [searchTerm, setSearchTerm] = useState('')
    const containerRef = useRef<HTMLDivElement>(null)

    // Filter options based on search term
    const filteredOptions = options.filter((opt) =>
        opt.name.toLowerCase().includes(searchTerm.toLowerCase())
    )

    // Get selected option
    const selectedOption = options.find((opt) => opt.id === value)

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (
                containerRef.current &&
                !containerRef.current.contains(event.target as Node)
            ) {
                setIsOpen(false)
            }
        }

        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const handleSelect = (optionId: string) => {
        onChange(optionId)
        setIsOpen(false)
        setSearchTerm('')
    }

    return (
        <div className="space-y-2" ref={containerRef}>
            {label && (
                <label className="text-sm font-semibold" style={{ color: '#151c27' }}>
                    {label}
                </label>
            )}

            {/* Button to open dropdown */}
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                disabled={disabled}
                className="w-full px-3 py-2 rounded-lg text-sm border text-left flex justify-between items-center"
                style={{
                    backgroundColor: '#f0f3ff',
                    borderColor: '#dce2f3',
                    color: selectedOption ? '#151c27' : '#727785',
                    opacity: disabled ? 0.6 : 1,
                    cursor: disabled ? 'not-allowed' : 'pointer',
                }}
            >
                <span>{selectedOption?.name || placeholder}</span>
                <svg
                    className="w-4 h-4"
                    style={{
                        color: '#727785',
                        transform: isOpen ? 'rotate(180deg)' : 'rotate(0)',
                        transition: 'transform 0.2s',
                    }}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 14l-7 7m0 0l-7-7m7 7V3"
                    />
                </svg>
            </button>

            {/* Dropdown Menu */}
            {isOpen && (
                <div
                    className="absolute z-50 w-80 rounded-lg border shadow-lg mt-1"
                    style={{
                        backgroundColor: '#ffffff',
                        borderColor: '#dce2f3',
                        maxHeight: '300px',
                        overflowY: 'auto',
                    }}
                >
                    {/* Search Input */}
                    <div className="sticky top-0 p-2 border-b bg-white" style={{ borderColor: '#dce2f3' }}>
                        <input
                            type="text"
                            placeholder="Tìm kiếm..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full px-2 py-1 rounded text-sm border"
                            style={{
                                backgroundColor: '#f0f3ff',
                                borderColor: '#c2c6d6',
                                color: '#151c27',
                            }}
                            autoFocus
                        />
                    </div>

                    {/* Options List */}
                    <ul className="py-1">
                        {filteredOptions.length > 0 ? (
                            filteredOptions.map((option) => (
                                <li
                                    key={option.id}
                                    onClick={() => handleSelect(option.id)}
                                    className="px-3 py-2 cursor-pointer hover:bg-blue-50 text-sm"
                                    style={{
                                        color: value === option.id ? '#0058be' : '#151c27',
                                        backgroundColor:
                                            value === option.id ? '#f0f3ff' : 'transparent',
                                        fontWeight: value === option.id ? '600' : '400',
                                    }}
                                >
                                    {option.name}
                                </li>
                            ))
                        ) : (
                            <li className="px-3 py-2 text-sm text-center" style={{ color: '#727785' }}>
                                Không tìm thấy kết quả
                            </li>
                        )}
                    </ul>

                    {/* Result count */}
                    <div
                        className="px-3 py-1 text-xs text-center border-t"
                        style={{
                            color: '#727785',
                            borderColor: '#dce2f3',
                            backgroundColor: '#f9f9ff',
                        }}
                    >
                        {filteredOptions.length} / {options.length} kết quả
                    </div>
                </div>
            )}

            {error && (
                <p className="text-xs" style={{ color: '#ba1a1a' }}>
                    {error}
                </p>
            )}
        </div>
    )
}
