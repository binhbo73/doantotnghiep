'use client'

import React, { useState, useEffect } from 'react'
import { PDFViewer } from './PDFViewer'
import { WordViewer } from './WordViewer'
import { ExcelViewer } from './ExcelViewer'

interface PreviewModalProps {
    isOpen: boolean
    onClose: () => void
    fileUrl: string
    fileName: string
    fileType: string
}

export function PreviewModal({ isOpen, onClose, fileUrl, fileName, fileType }: PreviewModalProps) {
    const [error, setError] = useState<string | null>(null)
    const [viewerStatus, setViewerStatus] = useState<{ label: string; current: number; total: number } | null>(null)

    useEffect(() => {
        setError(null)
        setViewerStatus(null)
    }, [fileUrl])

    if (!isOpen) return null

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

    const handleWordScrollStatsChange = (currentPage: number, totalPages: number) => {
        setViewerStatus({ label: 'Trang', current: currentPage, total: totalPages })
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
                        <WordViewer
                            fileUrl={fileUrl}
                            onLoadSuccess={handleLoadSuccess}
                            onLoadError={handleLoadError}
                            onScrollStatsChange={handleWordScrollStatsChange}
                        />
                    )}

                    {!error && isExcel && (
                        <ExcelViewer
                            fileUrl={fileUrl}
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
