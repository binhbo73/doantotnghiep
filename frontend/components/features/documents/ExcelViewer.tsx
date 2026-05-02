'use client'

import React, { useState, useEffect, useRef } from 'react'
import * as XLSX from 'xlsx'

interface ExcelViewerProps {
    fileUrl: string
    onLoadSuccess: () => void
    onLoadError: (error: Error) => void
    onSheetChange?: (activeSheet: number, totalSheets: number) => void
}

interface SheetData {
    name: string
    data: (string | number)[][]
}

export function ExcelViewer({ fileUrl, onLoadSuccess, onLoadError, onSheetChange }: ExcelViewerProps) {
    const [sheets, setSheets] = useState<SheetData[]>([])
    const [activeSheet, setActiveSheet] = useState(0)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const onLoadSuccessRef = useRef(onLoadSuccess)
    const onLoadErrorRef = useRef(onLoadError)
    const onSheetChangeRef = useRef(onSheetChange)

    useEffect(() => {
        onLoadSuccessRef.current = onLoadSuccess
    }, [onLoadSuccess])

    useEffect(() => {
        onLoadErrorRef.current = onLoadError
    }, [onLoadError])

    useEffect(() => {
        onSheetChangeRef.current = onSheetChange
    }, [onSheetChange])

    useEffect(() => {
        const loadExcel = async () => {
            setIsLoading(true)
            setError(null)
            try {
                const response = await fetch(fileUrl)
                const arrayBuffer = await response.arrayBuffer()
                const workbook = XLSX.read(arrayBuffer, { type: 'array' })

                const sheetsData: SheetData[] = workbook.SheetNames.map((sheetName) => {
                    const worksheet = workbook.Sheets[sheetName]
                    const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as (string | number)[][]
                    return {
                        name: sheetName,
                        data: jsonData,
                    }
                })

                setSheets(sheetsData)
                onSheetChangeRef.current?.(0, sheetsData.length)
                onLoadSuccessRef.current()
            } catch (err) {
                const error = err instanceof Error ? err : new Error('Unknown error')
                console.error('Excel loading error:', error)
                setError('Không thể tải file Excel')
                onLoadErrorRef.current(error)
            } finally {
                setIsLoading(false)
            }
        }

        loadExcel()
    }, [fileUrl])

    useEffect(() => {
        if (sheets.length > 0) {
            onSheetChangeRef.current?.(activeSheet, sheets.length)
        }
    }, [activeSheet, sheets.length])

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 h-full">
                <div className="w-12 h-12 rounded-full border-4 border-slate-300 border-t-slate-600 animate-spin"></div>
                <p className="text-slate-400 text-sm">Đang tải file Excel...</p>
            </div>
        )
    }

    if (error || sheets.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 h-full p-6">
                <span className="material-symbols-outlined text-5xl text-red-400">error</span>
                <p className="text-red-400 text-sm text-center">{error || 'File Excel trống'}</p>
            </div>
        )
    }

    const currentSheet = sheets[activeSheet]

    return (
        <div className="w-full h-full flex flex-col bg-white">
            {/* Sheet Tabs */}
            {sheets.length > 1 && (
                <div className="flex gap-2 px-6 py-3 border-b border-slate-200 bg-slate-50 overflow-x-auto">
                    {sheets.map((sheet, idx) => (
                        <button
                            key={idx}
                            onClick={() => setActiveSheet(idx)}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex-shrink-0 ${activeSheet === idx
                                ? 'bg-slate-800 text-white'
                                : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
                                }`}
                        >
                            {sheet.name}
                        </button>
                    ))}
                </div>
            )}

            {/* Table Content */}
            <div className="flex-1 overflow-auto p-4">
                <table className="border-collapse text-sm">
                    <tbody>
                        {currentSheet.data.map((row, rowIdx) => (
                            <tr key={rowIdx}>
                                {row.map((cell, cellIdx) => (
                                    <td
                                        key={cellIdx}
                                        className={`border border-slate-300 px-4 py-2 text-left ${rowIdx === 0
                                            ? 'bg-slate-100 font-bold text-slate-900'
                                            : 'bg-white text-slate-700'
                                            } ${cellIdx === 0 ? 'font-medium' : ''}`}
                                    >
                                        {cell}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
                {currentSheet.data.length === 0 && (
                    <div className="flex items-center justify-center h-full text-slate-400">
                        Sheet trống
                    </div>
                )}
            </div>
        </div>
    )
}
