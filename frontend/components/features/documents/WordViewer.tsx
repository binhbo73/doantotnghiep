'use client'

import React, { useState, useEffect, useRef } from 'react'
import { api } from '@/services/api/client'

interface WordViewerProps {
    fileUrl: string
    onLoadSuccess: () => void
    onLoadError: (error: Error) => void
    onScrollStatsChange?: (currentPage: number, totalPages: number) => void
}

export function WordViewer({ fileUrl, onLoadSuccess, onLoadError, onScrollStatsChange }: WordViewerProps) {
    const [htmlContent, setHtmlContent] = useState<string>('')
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [progress, setProgress] = useState<string>('Initializing...')
    const containerRef = useRef<HTMLDivElement | null>(null)
    const onLoadSuccessRef = useRef(onLoadSuccess)
    const onLoadErrorRef = useRef(onLoadError)
    const onScrollStatsChangeRef = useRef(onScrollStatsChange)

    useEffect(() => {
        onLoadSuccessRef.current = onLoadSuccess
    }, [onLoadSuccess])

    useEffect(() => {
        onLoadErrorRef.current = onLoadError
    }, [onLoadError])

    useEffect(() => {
        onScrollStatsChangeRef.current = onScrollStatsChange
    }, [onScrollStatsChange])

    useEffect(() => {
        let cancelled = false

        const loadWord = async () => {
            setIsLoading(true)
            setError(null)
            setProgress('Tải preview...')
            try {
                console.log('Loading Word preview from:', fileUrl)
                setProgress('Fetching preview HTML...')

                const response = await api.get<any>(fileUrl)
                if (cancelled) return

                const htmlBody = response?.data?.html ?? response?.html ?? response?.data
                if (typeof htmlBody !== 'string' || !htmlBody.trim()) {
                    throw new Error('Invalid preview response')
                }

                const inlineStyles = `
                    <style>
                        .docx-preview { width: 100%; color: #0f172a; font-size: 14px; line-height: 1.7; }
                        .docx-preview table { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
                        .docx-preview th,
                        .docx-preview td { border: 1px solid #d1d5db; padding: 0.55rem; vertical-align: top; }
                        .docx-preview p { margin: 0 0 1rem; }
                        .docx-preview h1,
                        .docx-preview h2,
                        .docx-preview h3,
                        .docx-preview h4 { margin: 1rem 0 0.75rem; }
                        .docx-preview ul,
                        .docx-preview ol { margin: 0 0 1rem 1.5rem; }
                        .docx-preview img { max-width: 100%; height: auto; }
                        .docx-preview blockquote { margin: 0 0 1rem; padding-left: 1rem; border-left: 3px solid #cbd5e1; color: #475569; }
                    </style>
                `

                setHtmlContent(inlineStyles + htmlBody)
                setProgress('Done')
                onLoadSuccessRef.current()
            } catch (err) {
                const error = err instanceof Error ? err : new Error(String(err))
                console.error('Word loading error:', error)
                setError(`Error: ${error.message}`)
                onLoadErrorRef.current(error)
            } finally {
                if (!cancelled) {
                    setIsLoading(false)
                }
            }
        }

        if (fileUrl) {
            loadWord()
        }

        return () => {
            cancelled = true
        }
    }, [fileUrl])

    useEffect(() => {
        const container = containerRef.current
        if (!container || isLoading || error || !htmlContent) return

        const updateStats = () => {
            const containerTop = container.getBoundingClientRect().top
            const threshold = containerTop + 140
            const pageHeight = Math.max(container.clientHeight, 1)
            const totalPages = Math.max(1, Math.ceil(container.scrollHeight / pageHeight))
            const currentPage = Math.min(totalPages, Math.max(1, Math.floor((container.scrollTop + threshold - containerTop) / pageHeight) + 1))
            onScrollStatsChangeRef.current?.(currentPage, totalPages)
        }

        updateStats()
        container.addEventListener('scroll', updateStats, { passive: true })
        window.addEventListener('resize', updateStats)

        return () => {
            container.removeEventListener('scroll', updateStats)
            window.removeEventListener('resize', updateStats)
        }
    }, [htmlContent, isLoading, error])

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center gap-4 h-full">
                <div className="w-12 h-12 rounded-full border-4 border-slate-300 border-t-slate-600 animate-spin"></div>
                <p className="text-slate-400 text-sm">Đang xử lý file...</p>
                <p className="text-slate-500 text-xs">{progress}</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 h-full p-6">
                <span className="material-symbols-outlined text-5xl text-red-400">error</span>
                <p className="text-red-400 text-sm text-center">{error}</p>
            </div>
        )
    }

    return (
        <div ref={containerRef} className="w-full h-full overflow-auto bg-slate-100 p-6">
            <div className="max-w-full mx-auto mb-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
                Xem trước Word hiển thị theo luồng nội dung gốc. Nếu cần đúng tuyệt đối, hãy tải xuống file gốc.
            </div>
            <div className="max-w-full mx-auto text-slate-900 font-serif leading-relaxed" style={{ fontSize: '14px' }}>
                <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
                    Xem trước có thể không giữ được 100% định dạng gốc. Nếu cần chính xác, hãy tải xuống file gốc.
                </div>
                <div
                    className="docx-preview bg-white rounded-lg p-6 text-slate-900"
                    style={{ lineHeight: '1.7' }}
                    dangerouslySetInnerHTML={{ __html: htmlContent }}
                />
            </div>
        </div>
    )
}
