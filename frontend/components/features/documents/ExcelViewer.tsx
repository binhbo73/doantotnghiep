'use client'

import React, { useState, useEffect, useMemo, useRef } from 'react'
import * as XLSX from 'xlsx'
import { buildApiUrl } from '@/config/api'
import { getAuthToken } from '@/services/auth'
import { logger } from '@/services/logger'

type AssetImageHint = {
    id?: string
    sheetName?: string
    anchorCell?: string
    imageEndpoint?: string
    caption?: string
}

interface ExcelViewerProps {
    fileUrl: string
    searchText?: string
    initialSheet?: number
    assetImage?: AssetImageHint
    assetImages?: AssetImageHint[]
    onLoadSuccess: () => void
    onLoadError: (error: Error) => void
    onSheetChange?: (activeSheet: number, totalSheets: number) => void
}

type CellValue = string | number | boolean

type MergeRange = {
    s: { r: number; c: number }
    e: { r: number; c: number }
}

type RenderMergeCell = {
    rowSpan: number
    colSpan: number
}

interface SheetData {
    name: string
    data: CellValue[][]
    merges: MergeRange[]
    colWidths: number[]
    rowHeights: number[]
    startRow: number
    startCol: number
    covered: Set<string>
    visible: Map<string, RenderMergeCell>
    mergeMap: Map<string, string>
    rows: XLSX.RowInfo[]
    cols: XLSX.ColInfo[]
}

function getExcelSearchTerms(searchText?: string): string[] {
    const cleaned = (searchText || '')
        .replace(/\[Nguon:[^\]]+\]/gi, ' ')
        .replace(/\[[0-9]+\]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()

    if (!cleaned) return []

    const phrases = cleaned
        .split(/(?:[.!?]\s+|;\s+)/)
        .map((part) => part.replace(/^[-*\d\s./)]+/, '').trim())
        .filter((part) => part.length >= 6)

    const keywords = cleaned
        .split(/\s+/)
        .map((part) => part.replace(/[^\p{L}\p{N}@._:/-]/gu, '').trim())
        .filter((part) => part.length >= 5)

    return Array.from(new Set([...phrases, ...keywords]))
        .sort((a, b) => b.length - a.length)
        .slice(0, 12)
}

function normalizeExcelSearchValue(value: string): string {
    return value
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/\u0111/g, 'd')
        .replace(/\u0110/g, 'd')
        .toLowerCase()
}

function scoreSheetForSearch(sheet: SheetData, searchTerms: string[]): number {
    if (!searchTerms.length) return 0
    const normalizedTerms = searchTerms.map(normalizeExcelSearchValue).filter(Boolean)
    let score = 0

    sheet.data.forEach((row) => {
        row.forEach((cell) => {
            const value = normalizeExcelSearchValue(String(cell || ''))
            if (!value) return
            normalizedTerms.forEach((term) => {
                if (value.includes(term)) {
                    score += term.length >= 18 ? 4 : 1
                }
            })
        })
    })

    return score
}

function getCellDisplayValue(worksheet: XLSX.WorkSheet, row: number, col: number): CellValue {
    const address = XLSX.utils.encode_cell({ r: row, c: col })
    const cell = worksheet[address]
    if (!cell) return ''
    const formatted = XLSX.utils.format_cell(cell)
    if (formatted !== undefined && formatted !== null) return formatted
    return cell.v === undefined || cell.v === null ? '' : String(cell.v)
}

function getColumnWidth(worksheet: XLSX.WorkSheet, col: number): number {
    const meta = worksheet['!cols']?.[col]
    const width = meta?.wpx || (meta?.wch ? Math.round(meta.wch * 7) : 88)
    return Math.min(320, Math.max(48, width))
}

function getRowHeight(worksheet: XLSX.WorkSheet, row: number): number {
    const meta = worksheet['!rows']?.[row]
    return Math.min(240, Math.max(28, meta?.hpx || 34))
}

function buildMergeMaps(merges: MergeRange[]) {
    const covered = new Set<string>()
    const visible = new Map<string, RenderMergeCell>()
    const mergeMap = new Map<string, string>()

    merges.forEach((merge) => {
        const rowSpan = merge.e.r - merge.s.r + 1
        const colSpan = merge.e.c - merge.s.c + 1
        const parentKey = `${merge.s.r}:${merge.s.c}`

        if (rowSpan <= 1 && colSpan <= 1) return

        visible.set(parentKey, { rowSpan, colSpan })
        for (let row = merge.s.r; row <= merge.e.r; row += 1) {
            for (let col = merge.s.c; col <= merge.e.c; col += 1) {
                const key = `${row}:${col}`
                mergeMap.set(key, parentKey)
                if (row === merge.s.r && col === merge.s.c) continue
                covered.add(key)
            }
        }
    })

    return { covered, visible, mergeMap }
}

function normalizeApiEndpoint(endpoint?: string) {
    if (!endpoint) return ''
    return endpoint.startsWith('/api/v1/') ? endpoint.slice('/api/v1'.length) : endpoint
}

function AuthenticatedExcelAssetImage({ assetImage }: { assetImage: AssetImageHint }) {
    // Priority: 1. /assets/{id}/image (standard API) 2. imageEndpoint (fallback)
    const endpoint = assetImage.id
        ? `/assets/${assetImage.id}/image`
        : normalizeApiEndpoint(assetImage.imageEndpoint)

    const [src, setSrc] = useState<string | null>(null)
    const [failed, setFailed] = useState(false)

    useEffect(() => {
        logger.debug('AuthenticatedExcelAssetImage loading endpoint', { endpoint, assetId: assetImage.id })
        if (!endpoint) {
            logger.warn('AuthenticatedExcelAssetImage missing endpoint', { assetId: assetImage.id })
            return
        }
        let objectUrl: string | null = null
        let cancelled = false

        const load = async () => {
            try {
                const token = getAuthToken()
                logger.debug('AuthenticatedExcelAssetImage fetching', { endpoint })
                const response = await fetch(buildApiUrl(endpoint), {
                    headers: {
                        ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    },
                })
                if (!response.ok) {
                    logger.error('AuthenticatedExcelAssetImage failed', { status: response.status })
                    throw new Error(`Cannot load asset image: ${response.status}`)
                }
                const blob = await response.blob()
                objectUrl = URL.createObjectURL(blob)
                logger.debug('AuthenticatedExcelAssetImage loaded successfully', { objectUrl })
                if (!cancelled) setSrc(objectUrl)
            } catch (err) {
                logger.error('AuthenticatedExcelAssetImage error', err)
                if (!cancelled) setFailed(true)
            }
        }

        load()
        return () => {
            cancelled = true
            if (objectUrl) URL.revokeObjectURL(objectUrl)
        }
    }, [endpoint])

    if (!endpoint || failed) {
        logger.warn('AuthenticatedExcelAssetImage returning null', { endpoint, failed })
        return null
    }
    if (!src) return <div className="h-40 min-w-48 animate-pulse rounded bg-slate-200" />

    return (
        <img
            src={src}
            alt={assetImage.caption || 'Anh minh chung'}
            className="my-2 max-h-[500px] w-auto max-w-full rounded border border-cyan-300 bg-white object-contain shadow-sm transition-transform hover:scale-[1.02]"
        />
    )
}

export function ExcelViewer({ fileUrl, searchText, initialSheet, assetImage, assetImages = [], onLoadSuccess, onLoadError, onSheetChange }: ExcelViewerProps) {
    const [sheets, setSheets] = useState<SheetData[]>([])
    const [activeSheet, setActiveSheet] = useState(0)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const onLoadSuccessRef = useRef(onLoadSuccess)
    const onLoadErrorRef = useRef(onLoadError)
    const onSheetChangeRef = useRef(onSheetChange)
    const searchTerms = useMemo(() => getExcelSearchTerms(searchText), [searchText])

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
                    let range = worksheet['!ref']
                        ? XLSX.utils.decode_range(worksheet['!ref'])
                        : { s: { r: 0, c: 0 }, e: { r: 0, c: 0 } }

                    // Expand range to include all assets for this sheet
                    assetImages.forEach(img => {
                        if (img.sheetName === sheetName && img.anchorCell) {
                            try {
                                const cell = XLSX.utils.decode_cell(img.anchorCell)
                                if (cell.r > range.e.r) range.e.r = cell.r
                                if (cell.c > range.e.c) range.e.c = cell.c
                                if (cell.r < range.s.r) range.s.r = cell.r
                                if (cell.c < range.s.c) range.s.c = cell.c
                            } catch (e) {
                                logger.warn(`Failed to decode anchor cell: ${img.anchorCell}`, e)
                            }
                        }
                    })

                    const data: CellValue[][] = []
                    for (let row = range.s.r; row <= range.e.r; row += 1) {
                        const rowData: CellValue[] = []
                        for (let col = range.s.c; col <= range.e.c; col += 1) {
                            rowData.push(getCellDisplayValue(worksheet, row, col))
                        }
                        data.push(rowData)
                    }

                    const colWidths = Array.from(
                        { length: range.e.c - range.s.c + 1 },
                        (_, idx) => getColumnWidth(worksheet, range.s.c + idx)
                    )
                    const rowHeights = Array.from(
                        { length: range.e.r - range.s.r + 1 },
                        (_, idx) => getRowHeight(worksheet, range.s.r + idx)
                    )

                    const merges = (worksheet['!merges'] || []) as MergeRange[]
                    const { covered, visible, mergeMap } = buildMergeMaps(merges)

                    return {
                        name: sheetName,
                        data,
                        merges,
                        colWidths,
                        rowHeights,
                        startRow: range.s.r,
                        startCol: range.s.c,
                        covered,
                        visible,
                        mergeMap,
                        rows: worksheet['!rows'] || [],
                        cols: worksheet['!cols'] || []
                    }
                })

                setSheets(sheetsData)
                const requestedSheet = Number(initialSheet || 1)
                const initialIndex = Number.isFinite(requestedSheet)
                    ? Math.min(Math.max(requestedSheet - 1, 0), Math.max(sheetsData.length - 1, 0))
                    : 0
                setActiveSheet(initialIndex)
                onSheetChangeRef.current?.(initialIndex, sheetsData.length)
                onLoadSuccessRef.current()
            } catch (err) {
                const error = err instanceof Error ? err : new Error('Unknown error')
                logger.error('Excel loading error', error)
                setError('Không thể tải file Excel')
                onLoadErrorRef.current(error)
            } finally {
                setIsLoading(false)
            }
        }

        loadExcel()
    }, [fileUrl, initialSheet, assetImages])

    useEffect(() => {
        if (!sheets.length || !initialSheet) return
        const nextSheet = Math.min(Math.max(Number(initialSheet) - 1, 0), sheets.length - 1)
        if (Number.isFinite(nextSheet) && nextSheet !== activeSheet) {
            setActiveSheet(nextSheet)
        }
    }, [activeSheet, initialSheet, sheets.length])

    useEffect(() => {
        if (sheets.length > 0) {
            onSheetChangeRef.current?.(activeSheet, sheets.length)
        }
    }, [activeSheet, sheets.length])

    useEffect(() => {
        if (!sheets.length || !searchTerms.length || assetImage?.anchorCell) return

        const ranked = sheets
            .map((sheet, index) => ({ index, score: scoreSheetForSearch(sheet, searchTerms) }))
            .sort((a, b) => b.score - a.score)
        const best = ranked[0]
        const currentScore = ranked.find((item) => item.index === activeSheet)?.score || 0

        if (best && best.score > 0 && best.index !== activeSheet && best.score > currentScore) {
            setActiveSheet(best.index)
        }
    }, [activeSheet, assetImage?.anchorCell, searchTerms, sheets])

    useEffect(() => {
        if (!isLoading && !error && assetImage?.anchorCell) {
            const cellId = assetImage.anchorCell.trim().toUpperCase()
            // Wait a bit for the table to render and stabilize
            const timer = setTimeout(() => {
                const element = document.getElementById(`cell-${cellId}`)
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' })
                    element.classList.add('ring-4', 'ring-cyan-400', 'ring-inset', 'z-10', 'relative')
                    setTimeout(() => {
                        element.classList.remove('ring-4', 'ring-cyan-400', 'ring-inset', 'z-10', 'relative')
                    }, 5000)
                }
            }, 800)
            return () => clearTimeout(timer)
        }
    }, [isLoading, error, assetImage, activeSheet])

    const visibleAssetImages = useMemo(() => {
        // Return all assets without duplicates by ID
        const allAssets = [...assetImages, ...(assetImage ? [assetImage] : [])]
        const uniqueMap = new Map<string, AssetImageHint>()

        allAssets.forEach((a) => {
            const key = a.id || a.imageEndpoint || `temp-${Math.random()}`
            if (!uniqueMap.has(key)) {
                uniqueMap.set(key, a)
            }
        })

        const result = Array.from(uniqueMap.values())
        logger.debug('ExcelViewer visible asset images', {
            count: result.length,
            preview: result.slice(0, 5).map((a) => ({ id: a.id, imageEndpoint: a.imageEndpoint })),
        })
        return result
    }, [assetImage, assetImages])

    const imagesByCell = useMemo(() => {
        if (!sheets.length) return new Map<string, AssetImageHint[]>()
        const map = new Map<string, AssetImageHint[]>()
        const sheet = sheets[activeSheet]
        if (!sheet) return map

        visibleAssetImages.forEach((img) => {
            if (img.sheetName === sheet.name && img.anchorCell) {
                let cellAddr = img.anchorCell.trim().toUpperCase()

                // Map image to parent cell if it's in a merge
                try {
                    const decoded = XLSX.utils.decode_cell(cellAddr)
                    const key = `${decoded.r}:${decoded.c}`
                    const parentKey = sheet.mergeMap.get(key)
                    if (parentKey) {
                        const [r, c] = parentKey.split(':').map(Number)
                        cellAddr = XLSX.utils.encode_cell({ r, c })
                    }
                } catch (e) { }

                if (!map.has(cellAddr)) {
                    map.set(cellAddr, [])
                }
                map.get(cellAddr)?.push(img)
            }
        })
        return map
    }, [visibleAssetImages, sheets, activeSheet])

    const galleryImages = useMemo(() => {
        const currentSheetName = sheets[activeSheet]?.name
        return visibleAssetImages.filter(img =>
            !img.sheetName ||
            img.sheetName !== currentSheetName ||
            !img.anchorCell
        )
    }, [visibleAssetImages, sheets, activeSheet])

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
    const { covered, visible } = currentSheet
    const isHighlightedCell = (cell: CellValue) => {
        if (searchTerms.length === 0) return false
        const value = normalizeExcelSearchValue(String(cell))
        return searchTerms.some((term) => value.includes(normalizeExcelSearchValue(term)))
    }

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

            {/* Asset Gallery */}
            {galleryImages.length > 0 && (
                <div className="border-b border-slate-200 bg-slate-50 p-4">
                    <h3 className="mb-3 text-sm font-semibold text-slate-700">
                        Hình ảnh minh chứng khác
                        <span className="ml-2 text-xs font-medium text-slate-500">({galleryImages.length})</span>
                    </h3>
                    <div className="flex flex-wrap gap-4">
                        {galleryImages.map((item, index) => (
                            <div key={item.id || item.imageEndpoint || `asset-${index}`} className="max-w-[420px]">
                                <AuthenticatedExcelAssetImage assetImage={item} />
                                <p className="mt-2 text-xs font-medium text-slate-500">
                                    {item.sheetName ? `Sheet ${item.sheetName}` : 'Không rõ sheet'}
                                    {item.anchorCell ? `, cell ${item.anchorCell}` : ''}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Table Content */}
            <div className="flex-1 overflow-auto p-4">
                <table className="border-collapse text-sm">
                    <colgroup>
                        <col style={{ width: 40, minWidth: 40 }} />
                        {currentSheet.colWidths.map((width, idx) => (
                            <col key={idx} style={{ width, minWidth: width }} />
                        ))}
                    </colgroup>
                    <thead>
                        <tr>
                            <th className="bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 p-1 text-xs font-medium text-slate-500 w-10 text-center sticky left-0 z-10">
                                #
                            </th>
                            {currentSheet.data[0]?.map((_, idx) => (
                                <th key={idx} className="bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 p-1 text-xs font-medium text-slate-500 min-w-[80px]">
                                    {XLSX.utils.encode_col(currentSheet.startCol + idx)}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {currentSheet.data.map((row, rowIdx) => {
                            const absoluteRow = currentSheet.startRow + rowIdx
                            const isHidden = currentSheet.rows[absoluteRow]?.hidden
                            if (isHidden) return null

                            return (
                                <tr
                                    key={rowIdx}
                                    style={{
                                        height: currentSheet.rowHeights[rowIdx],
                                    }}
                                    className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors"
                                >
                                    <td className="bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-600 p-1 text-[10px] font-medium text-slate-400 text-center sticky left-0 z-10">
                                        {absoluteRow + 1}
                                    </td>
                                    {row.map((cell, cellIdx) => {
                                        const absoluteCol = currentSheet.startCol + cellIdx
                                        const key = `${absoluteRow}:${absoluteCol}`
                                        if (covered.has(key)) return null
                                        const merge = visible.get(key)

                                        return (
                                            <td
                                                key={cellIdx}
                                                id={`cell-${XLSX.utils.encode_cell({ r: absoluteRow, c: absoluteCol })}`}
                                                rowSpan={merge?.rowSpan}
                                                colSpan={merge?.colSpan}
                                                className={`border border-slate-300 px-2 py-1 text-left align-top leading-snug transition-all duration-500 ${isHighlightedCell(cell)
                                                    ? 'bg-amber-100 font-semibold text-slate-900'
                                                    : rowIdx === 0
                                                        ? 'bg-slate-100 font-bold text-slate-900'
                                                        : 'bg-white text-slate-700'
                                                    } ${cellIdx === 0 ? 'font-medium' : ''}`}
                                                style={{
                                                    minWidth: currentSheet.colWidths[cellIdx],
                                                    maxWidth: currentSheet.colWidths[cellIdx] * (merge?.colSpan || 1),
                                                }}
                                            >
                                                <div className="whitespace-pre-wrap break-words">{cell}</div>
                                                {(() => {
                                                    const cellAddress = XLSX.utils.encode_cell({ r: absoluteRow, c: absoluteCol })
                                                    const cellImages = imagesByCell.get(cellAddress)
                                                    if (!cellImages || cellImages.length === 0) return null
                                                    return (
                                                        <div className="mt-2 flex flex-col gap-3">
                                                            {cellImages.map((img, i) => (
                                                                <div key={img.id || i} className="relative group">
                                                                    <AuthenticatedExcelAssetImage assetImage={img} />
                                                                    <div className="absolute top-2 left-2 px-2 py-1 bg-black/50 backdrop-blur-sm rounded text-[10px] text-white opacity-0 group-hover:opacity-100 transition-opacity">
                                                                        {img.anchorCell}
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )
                                                })()}
                                            </td>
                                        )
                                    })}
                                </tr>
                            )
                        })}
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
