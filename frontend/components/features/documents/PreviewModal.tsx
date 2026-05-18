'use client'

import React, { useState, useEffect } from 'react'
import { PDFViewer } from './PDFViewer'
import { ExcelViewer } from './ExcelViewer'
import { buildApiUrl } from '@/config/api'

interface PreviewModalProps {
    isOpen: boolean
    onClose: () => void
    documentId?: string
    fileUrl: string
    fileName: string
    fileType: string
}

type DocumentAssetSource = {
    id: string
    page_number?: number | null
    sheet_name?: string | null
    anchor_cell?: string | null
    caption?: string | null
    image_url?: string | null
}

type ExcelAssetImage = {
    id?: string
    sheetName?: string
    anchorCell?: string
    imageEndpoint?: string
    caption?: string
}

function normalizeApiEndpoint(endpoint?: string | null): string {
    if (!endpoint) return ''
    return endpoint.startsWith('/api/v1/') ? endpoint.slice('/api/v1'.length) : endpoint
}

function OriginalFileViewer({ fileUrl, fileName, onLoadSuccess }: { fileUrl: string; fileName: string; onLoadSuccess: () => void }) {
    useEffect(() => {
        onLoadSuccess()
    }, [onLoadSuccess])

    return (
        <div className="flex h-full w-full flex-col bg-white">
            <iframe
                src={fileUrl}
                title={fileName}
                className="min-h-0 flex-1 border-0 bg-white"
            />
            <div className="border-t border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
                Opening the original file. If this browser cannot display the format, open it with Office on your machine.
            </div>
        </div>
    )
}

export function PreviewModal({ isOpen, onClose, documentId, fileUrl, fileName, fileType }: PreviewModalProps) {
    const [error, setError] = useState<string | null>(null)
    const [viewerStatus, setViewerStatus] = useState<{ label: string; current: number; total: number } | null>(null)
    const [excelAssetImages, setExcelAssetImages] = useState<ExcelAssetImage[]>([])

    useEffect(() => {
        setError(null)
        setViewerStatus(null)
    }, [fileUrl])

    // Detect file types - handle both MIME types and extensions
    const fileTypeNorm = fileType.toLowerCase().trim()
    console.log('Preview file type:', fileTypeNorm, 'from fileType:', fileType)

    // MIME type detection
    const isPDF = fileTypeNorm === 'pdf' || fileTypeNorm === 'application/pdf'
    const isWord =
        fileTypeNorm === 'doc' ||
        fileTypeNorm === 'docx' ||
        fileTypeNorm === '.doc' ||
        fileTypeNorm === '.docx' ||
        fileTypeNorm === 'application/msword' ||
        fileTypeNorm === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

    const isExcel =
        fileTypeNorm === 'xls' ||
        fileTypeNorm === 'xlsx' ||
        fileTypeNorm === '.xls' ||
        fileTypeNorm === '.xlsx' ||
        fileTypeNorm === 'application/vnd.ms-excel' ||
        fileTypeNorm === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    const isText =
        fileTypeNorm === 'txt' ||
        fileTypeNorm === 'text' ||
        fileTypeNorm === 'text/plain' ||
        fileTypeNorm === 'md' ||
        fileTypeNorm === 'markdown' ||
        fileTypeNorm === 'text/markdown'

    const isImage =
        ['jpg', 'jpeg', 'png', 'gif', 'webp', '.jpg', '.jpeg', '.png', '.gif', '.webp'].includes(fileTypeNorm) ||
        fileTypeNorm.startsWith('image/')

    const isSupported = isPDF || isWord || isExcel || isImage || isText

    console.log('File detection:', { isPDF, isWord, isExcel, isImage, isText, isSupported, error, fileUrl })

    useEffect(() => {
        if (!isOpen || !isExcel || !documentId) {
            setExcelAssetImages([])
            return
        }

        let cancelled = false
        const controller = new AbortController()

        const loadExcelAssets = async () => {
            try {
                const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
                const response = await fetch(buildApiUrl(`/documents/${documentId}/assets`), {
                    headers: {
                        ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    },
                    signal: controller.signal,
                })

                if (!response.ok) {
                    if (!cancelled) setExcelAssetImages([])
                    return
                }

                const body = await response.json()
                const data = body?.data || body
                const assets = Array.isArray(data) ? data as DocumentAssetSource[] : []
                const mapped = assets
                    .map((asset) => ({
                        id: asset.id,
                        sheetName: asset.sheet_name || undefined,
                        anchorCell: asset.anchor_cell || undefined,
                        imageEndpoint: asset.image_url ? normalizeApiEndpoint(asset.image_url) : `/assets/${asset.id}/image`,
                        caption: asset.caption || undefined,
                    }))

                if (!cancelled) setExcelAssetImages(mapped)
            } catch (err) {
                if ((err as Error).name !== 'AbortError' && !cancelled) {
                    setExcelAssetImages([])
                }
            }
        }

        loadExcelAssets()

        return () => {
            cancelled = true
            controller.abort()
        }
    }, [isOpen, isExcel, documentId])

    if (!isOpen) return null

    const handleLoadSuccess = () => {
        console.log('✅ Document loaded successfully')
    }

    const handlePdfLoadSuccess = (pages: number) => {
        handleLoadSuccess()
        setViewerStatus({ label: 'Trang', current: 1, total: pages })
    }

    const handlePdfPageChange = (page: number) => {
        setViewerStatus((previous) => {
            if (!previous) {
                return { label: 'Trang', current: page, total: 0 }
            }

            return { ...previous, label: 'Trang', current: page }
        })
    }

    const handleExcelSheetChange = (activeSheet: number, totalSheets: number) => {
        setViewerStatus({ label: 'Sheet', current: activeSheet + 1, total: totalSheets })
    }

    const handleLoadError = (error: Error) => {
        console.error('❌ Document load error:', error)
        setError('Không thể tải file. Vui lòng thử lại.')
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm px-4 py-4">
            <div className="relative w-full h-full max-w-[95vw] lg:max-w-[85vw] xl:max-w-[75vw] max-h-[90vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-slate-50 to-slate-100">
                    <div className="flex-1 min-w-0">
                        <h2 className="text-lg font-bold text-slate-900 truncate">{fileName}</h2>
                        <p className="text-xs text-slate-500 mt-1">
                            {isPDF && 'Tài liệu PDF'}
                            {isWord && 'Tài liệu Word'}
                            {isText && 'Văn bản / Markdown'}
                            {isExcel && 'Bảng tính Excel'}
                            {isImage && 'Hình ảnh'}
                        </p>
                    </div>

                    <button
                        onClick={onClose}
                        className="ml-4 w-9 h-9 rounded-lg bg-slate-200 hover:bg-slate-300 flex items-center justify-center text-slate-600 hover:text-slate-900 transition-colors flex-shrink-0"
                        title="Đóng"
                    >
                        <span className="material-symbols-outlined text-xl">close</span>
                    </button>
                </div>

                {/* Content Area */}
                <div className="flex-1 min-h-0 overflow-auto bg-slate-50 flex items-center justify-center">
                    {error && (
                        <div className="flex flex-col items-center justify-center gap-3 p-6">
                            <span className="material-symbols-outlined text-5xl text-red-400">error</span>
                            <p className="text-red-400 text-sm text-center">{error}</p>
                            <p className="text-slate-400 text-xs text-center max-w-sm">
                                Vui lòng tải xuống để xem file này
                            </p>
                        </div>
                    )}

                    {!error && isPDF && (
                        <div className="bg-white p-3 rounded-lg shadow-lg w-full h-full min-h-0 overflow-hidden">
                            <PDFViewer
                                fileUrl={fileUrl}
                                onLoadSuccess={handlePdfLoadSuccess}
                                onLoadError={handleLoadError}
                                onPageChange={handlePdfPageChange}
                            />
                        </div>
                    )}

                    {!error && (isWord || isText) && (
                        <OriginalFileViewer
                            fileUrl={fileUrl}
                            fileName={fileName}
                            onLoadSuccess={handleLoadSuccess}
                        />
                    )}

                    {!error && isExcel && (
                        <ExcelViewer
                            fileUrl={fileUrl}
                            assetImages={excelAssetImages}
                            onLoadSuccess={handleLoadSuccess}
                            onLoadError={handleLoadError}
                            onSheetChange={handleExcelSheetChange}
                        />
                    )}

                    {!error && isImage && (
                        <img
                            src={fileUrl}
                            alt={fileName}
                            className="max-w-full max-h-full object-contain"
                        />
                    )}

                    {/* text is handled by backend preview + WordViewer */}

                    {!error && !isSupported && (
                        <div className="flex flex-col items-center justify-center gap-3 p-6">
                            <span className="material-symbols-outlined text-5xl text-slate-400">description</span>
                            <p className="text-slate-700 text-sm font-medium">Định dạng không được hỗ trợ</p>
                            <p className="text-slate-400 text-xs text-center">
                                Định dạng {fileType.toUpperCase()} không thể xem trực tiếp. Vui lòng tải xuống để xem.
                            </p>
                            <p className="text-slate-500 text-xs mt-2 text-center max-w-sm">
                                Hỗ trợ: PDF, Word (.doc, .docx), Excel (.xls, .xlsx), TXT, Markdown, Hình ảnh (JPG, PNG, GIF, WebP)
                            </p>
                        </div>
                    )}
                </div>

                <div className="flex items-center justify-between gap-3 px-6 py-4 border-t border-slate-200 bg-gradient-to-r from-slate-50 to-slate-100">
                    <div className="text-xs font-medium text-slate-600">
                        {viewerStatus ? `${viewerStatus.label} ${viewerStatus.current} / ${viewerStatus.total}` : ' '}
                    </div>

                    <button
                        onClick={onClose}
                        className="px-4 py-1.5 text-sm font-medium text-white bg-slate-800 hover:bg-slate-900 rounded-lg transition-colors"
                    >
                        Đóng
                    </button>
                </div>
            </div>
        </div>
    )
}
