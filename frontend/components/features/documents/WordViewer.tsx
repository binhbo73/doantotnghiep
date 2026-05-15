'use client'

import React, { useState, useEffect, useRef } from 'react'
import { api } from '@/services/api/client'

interface WordViewerProps {
    fileUrl: string
    searchText?: string
    onLoadSuccess: () => void
    onLoadError: (error: Error) => void
    onScrollStatsChange?: (currentPage: number, totalPages: number) => void
}

function getSearchPhrases(searchText?: string): string[] {
    const cleaned = (searchText || '')
        .replace(/\[Nguon:[^\]]+\]/gi, ' ')
        .replace(/\[[0-9]+\]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()

    if (!cleaned) return []

    const chunks = cleaned
        .split(/(?:[.!?]\s+|\n+|;\s+)/)
        .map((part) => part.replace(/^[-*\d\s./)]+/, '').trim())
        .filter((part) => part.length >= 12)

    return Array.from(new Set(chunks))
        .sort((a, b) => b.length - a.length)
        .slice(0, 8)
}

function highlightPreviewHtml(html: string, searchText?: string): string {
    if (typeof window === 'undefined') return html

    const phrases = getSearchPhrases(searchText)
    if (phrases.length === 0) return html

    const parser = new DOMParser()
    const document = parser.parseFromString(`<div>${html}</div>`, 'text/html')
    const root = document.body.firstElementChild
    if (!root) return html

    const textNodes: Text[] = []
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
        acceptNode(node) {
            const parentName = node.parentElement?.tagName.toLowerCase()
            if (!node.nodeValue?.trim() || parentName === 'style' || parentName === 'script' || parentName === 'mark') {
                return NodeFilter.FILTER_REJECT
            }
            return NodeFilter.FILTER_ACCEPT
        },
    })

    let currentNode = walker.nextNode()
    while (currentNode) {
        textNodes.push(currentNode as Text)
        currentNode = walker.nextNode()
    }

    textNodes.forEach((node) => {
        const text = node.nodeValue || ''
        const lowerText = text.toLowerCase()
        const matches: { start: number; end: number }[] = []

        phrases.forEach((phrase) => {
            const needle = phrase.toLowerCase()
            let index = lowerText.indexOf(needle)
            while (index !== -1) {
                matches.push({ start: index, end: index + phrase.length })
                index = lowerText.indexOf(needle, index + phrase.length)
            }
        })

        if (matches.length === 0) return

        const merged = matches
            .sort((a, b) => a.start - b.start || b.end - a.end)
            .reduce<{ start: number; end: number }[]>((items, match) => {
                const previous = items[items.length - 1]
                if (previous && match.start <= previous.end) {
                    previous.end = Math.max(previous.end, match.end)
                    return items
                }
                items.push({ ...match })
                return items
            }, [])

        const fragment = document.createDocumentFragment()
        let cursor = 0
        merged.forEach((match) => {
            if (match.start > cursor) {
                fragment.appendChild(document.createTextNode(text.slice(cursor, match.start)))
            }
            const mark = document.createElement('mark')
            mark.className = 'citation-preview-highlight'
            mark.textContent = text.slice(match.start, match.end)
            fragment.appendChild(mark)
            cursor = match.end
        })

        if (cursor < text.length) {
            fragment.appendChild(document.createTextNode(text.slice(cursor)))
        }

        node.parentNode?.replaceChild(fragment, node)
    })

    return root.innerHTML
}

export function WordViewer({ fileUrl, searchText, onLoadSuccess, onLoadError, onScrollStatsChange }: WordViewerProps) {
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
                        .docx-preview .citation-preview-highlight { background: #fde68a; color: inherit; border-radius: 4px; padding: 0 2px; box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.16); }
                    </style>
                `

                setHtmlContent(inlineStyles + highlightPreviewHtml(htmlBody, searchText))
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
    }, [fileUrl, searchText])

    useEffect(() => {
        const container = containerRef.current
        if (!container || isLoading || error || !htmlContent) return

        const firstHighlight = container.querySelector('.citation-preview-highlight')
        if (firstHighlight) {
            window.setTimeout(() => {
                firstHighlight.scrollIntoView({ block: 'center', behavior: 'smooth' })
            }, 100)
        }

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
