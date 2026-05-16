'use client'

import React, { Suspense, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { ExcelViewer } from '@/components/features/documents/ExcelViewer'
import { PDFViewer } from '@/components/features/documents/PDFViewer'
import { WordViewer } from '@/components/features/documents/WordViewer'
import { buildApiUrl } from '@/config/api'

type CitationViewerPayload = {
    document_id?: string
    title?: string
    type?: string
    page?: string | number
    chunk_index?: number
    chunk_id?: string
    start_char?: number
    end_char?: number
    line_start?: number
    line_end?: number
    answer_context?: string
    excerpt?: string
    description?: string
    url?: string
}

type SearchTextSource = 'chunk' | 'excerpt' | 'description' | 'answer_context' | 'none'

type CitationTarget = {
    documentId?: string
    chunkId?: string
    page?: number
    chunkIndex?: number
    startChar?: number
    endChar?: number
    lineStart?: number
    lineEnd?: number
}

type ViewerKind = 'pdf' | 'word' | 'excel' | 'image' | 'unsupported'

type ViewerState = {
    kind: ViewerKind
    fileUrl: string
    fileType: string
}

type CitationChunkSource = {
    id: string
    document_id: string
    content: string
    chunk_index?: number
    page_number?: number
    start_char?: number
    end_char?: number
    line_start?: number
    line_end?: number
}

function normalizeForSectionMatch(value?: string) {
    return (value || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/\u0111/g, 'd')
        .replace(/\u0110/g, 'd')
        .toLowerCase()
}

function getPrimaryChunkSection(chunkContent?: string, preferredText?: string): string {
    const content = (chunkContent || '').trim()
    if (!content) return ''

    const headingPattern = /(?:^|\n|\s-\s+)(?:[-+*]\s*)?\d{1,2}\/\s+[^?]+\?/g
    const matches = Array.from(content.matchAll(headingPattern))
    if (!matches.length) return content

    const sections = matches
        .map((match, index) => {
            const start = match.index || 0
            const end = index + 1 < matches.length ? matches[index + 1].index || content.length : content.length
            return content.slice(start, end).replace(/^\s*-\s*/, '').trim()
        })
        .filter(Boolean)

    if (!sections.length) return content

    const preferred = normalizeForSectionMatch(preferredText)
    if (preferred) {
        const preferredTokens = new Set(
            preferred
                .split(/[^a-z0-9]+/i)
                .filter((token) => token.length >= 3)
        )
        const best = sections
            .map((section) => {
                const sectionNorm = normalizeForSectionMatch(section)
                let score = 0
                preferredTokens.forEach((token) => {
                    if (sectionNorm.includes(token)) score += 1
                })
                return { section, score }
            })
            .sort((a, b) => b.score - a.score)[0]

        if (best?.score > 0) return best.section
    }

    return sections[0]
}

function getFileExtension(title?: string): string {
    const match = title?.toLowerCase().match(/\.([a-z0-9]+)(?:$|\?)/)
    return match?.[1] || ''
}

function getFilenameFromContentDisposition(header?: string | null): string {
    if (!header) return ''

    const encodedMatch = header.match(/filename\*=UTF-8''([^;]+)/i)
    if (encodedMatch?.[1]) {
        try {
            return decodeURIComponent(encodedMatch[1].replace(/"/g, ''))
        } catch {
            return encodedMatch[1].replace(/"/g, '')
        }
    }

    const plainMatch = header.match(/filename="?([^";]+)"?/i)
    return plainMatch?.[1] || ''
}

function classifyFileType(type?: string, title?: string, contentType?: string): ViewerKind {
    const normalizedType = (type || '').toLowerCase().trim()
    const normalizedContentType = (contentType || '').toLowerCase().trim()
    const extension = getFileExtension(title)
    const candidates = [normalizedType, normalizedContentType, extension].filter(Boolean)

    if (candidates.some((value) => value === 'pdf' || value === '.pdf' || value.includes('application/pdf'))) {
        return 'pdf'
    }

    if (candidates.some((value) => (
        ['doc', 'docx', '.doc', '.docx'].includes(value) ||
        value.includes('application/msword') ||
        value.includes('wordprocessingml.document')
    ))) {
        return 'word'
    }

    if (candidates.some((value) => (
        ['txt', 'text', 'md', 'markdown', '.txt', '.md'].includes(value) ||
        value.includes('text/plain') ||
        value.includes('text/markdown')
    ))) {
        return 'word'
    }

    if (candidates.some((value) => (
        ['xls', 'xlsx', 'csv', '.xls', '.xlsx', '.csv'].includes(value) ||
        value.includes('application/vnd.ms-excel') ||
        value.includes('spreadsheetml.sheet') ||
        value.includes('text/csv')
    ))) {
        return 'excel'
    }

    if (candidates.some((value) => (
        ['jpg', 'jpeg', 'png', 'gif', 'webp', '.jpg', '.jpeg', '.png', '.gif', '.webp'].includes(value) ||
        value.startsWith('image/')
    ))) {
        return 'image'
    }

    return 'unsupported'
}

function getViewerLabel(kind?: ViewerKind): string {
    switch (kind) {
        case 'pdf':
            return 'Tai lieu PDF'
        case 'word':
            return 'Tai lieu Word / van ban'
        case 'excel':
            return 'Bang tinh Excel'
        case 'image':
            return 'Hinh anh'
        default:
            return 'Tai lieu nguon'
    }
}

function CitationViewerContent() {
    const searchParams = useSearchParams()
    const [viewer, setViewer] = useState<ViewerState | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [pageCount, setPageCount] = useState(0)
    const [searchDebug, setSearchDebug] = useState<{ source: SearchTextSource, len: number, preview: string } | null>(null)
    const [chunkSource, setChunkSource] = useState<CitationChunkSource | null>(null)

    const payload = useMemo<CitationViewerPayload>(() => {
        const storageKey = searchParams.get('key')
        if (storageKey && typeof window !== 'undefined') {
            try {
                const raw = sessionStorage.getItem(storageKey)
                if (raw) return JSON.parse(raw)
            } catch (err) {
                console.error('Failed to read citation payload:', err)
            }
        }

        return {
            document_id: searchParams.get('documentId') || undefined,
            title: searchParams.get('title') || undefined,
            type: searchParams.get('type') || undefined,
            page: searchParams.get('page') || undefined,
            excerpt: searchParams.get('q') || undefined,
        }
    }, [searchParams])

    useEffect(() => {
        if (!payload.document_id || !payload.chunk_id) {
            setChunkSource(null)
            return
        }

        const controller = new AbortController()
        const loadChunkSource = async () => {
            try {
                const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
                const response = await fetch(buildApiUrl(`/documents/${payload.document_id}/chunks/${payload.chunk_id}`), {
                    headers: {
                        ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    },
                    signal: controller.signal,
                })

                if (!response.ok) {
                    setChunkSource(null)
                    return
                }

                const body = await response.json()
                setChunkSource((body?.data || body) as CitationChunkSource)
            } catch (err) {
                if ((err as Error).name !== 'AbortError') {
                    setChunkSource(null)
                }
            }
        }

        loadChunkSource()

        return () => controller.abort()
    }, [payload.document_id, payload.chunk_id])

    const initialPage = Number(chunkSource?.page_number || payload.page || 1)
    const preferredCitationText = payload.answer_context || payload.excerpt || payload.description || ''
    const chunkSectionText = getPrimaryChunkSection(chunkSource?.content, preferredCitationText)
    // chunkSource.content thuong overlap voi chunk ke tiep, nen chi truyen section chinh
    // cua chunk xuong viewer. Neu co answer_context/excerpt thi do moi la doan can to.
    // answer_context la cau tra loi cua LLM, chi dung hien thi/doi chieu, khong lam neo chinh.
    const searchText = preferredCitationText || chunkSectionText || chunkSource?.content || ''
    const chunkText = chunkSectionText || chunkSource?.content || ''
    const answerContext = payload.answer_context || ''
    const citationTarget = useMemo<CitationTarget>(() => ({
        documentId: payload.document_id,
        chunkId: chunkSource?.id || payload.chunk_id,
        page: Number.isFinite(initialPage) && initialPage > 0 ? initialPage : undefined,
        chunkIndex: typeof chunkSource?.chunk_index === 'number' ? chunkSource.chunk_index : typeof payload.chunk_index === 'number' ? payload.chunk_index : undefined,
        startChar: typeof chunkSource?.start_char === 'number' ? chunkSource.start_char : typeof payload.start_char === 'number' ? payload.start_char : undefined,
        endChar: typeof chunkSource?.end_char === 'number' ? chunkSource.end_char : typeof payload.end_char === 'number' ? payload.end_char : undefined,
        lineStart: typeof chunkSource?.line_start === 'number' ? chunkSource.line_start : typeof payload.line_start === 'number' ? payload.line_start : undefined,
        lineEnd: typeof chunkSource?.line_end === 'number' ? chunkSource.line_end : typeof payload.line_end === 'number' ? payload.line_end : undefined,
    }), [payload, initialPage, chunkSource])
    const targetLabel = [
        citationTarget.page ? `trang ${citationTarget.page}` : '',
        typeof citationTarget.chunkIndex === 'number' ? `chunk ${citationTarget.chunkIndex}` : '',
        citationTarget.lineStart ? (
            citationTarget.lineEnd && citationTarget.lineEnd !== citationTarget.lineStart
                ? `dong ${citationTarget.lineStart}-${citationTarget.lineEnd}`
                : `dong ${citationTarget.lineStart}`
        ) : '',
    ].filter(Boolean).join(', ')

    // Update debug info
    useEffect(() => {
        const source: SearchTextSource = payload.answer_context ? 'answer_context' : payload.excerpt ? 'excerpt' : payload.description ? 'description' : chunkText ? 'chunk' : 'none'
        setSearchDebug(searchText ? {
            source,
            len: searchText.length,
            preview: searchText.substring(0, 150).replace(/\n/g, ' ')
        } : null)
    }, [searchText, chunkText, payload])
    const title = payload.title || 'Tai lieu nguon'
    const guessedKind = classifyFileType(payload.type, title)

    useEffect(() => {
        let objectUrl = ''
        const controller = new AbortController()

        const loadSource = async () => {
            try {
                setError(null)
                setViewer(null)
                const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
                const endpoint = payload.url || (payload.document_id ? `/documents/${payload.document_id}/download` : '')
                if (!endpoint) {
                    throw new Error('Khong co document_id de mo nguon')
                }

                const initialKind = classifyFileType(payload.type, title)

                if (initialKind === 'word' && payload.document_id) {
                    setViewer({
                        kind: 'word',
                        fileUrl: `/documents/${payload.document_id}/preview`,
                        fileType: payload.type || getFileExtension(title) || 'text',
                    })
                    return
                }

                const response = await fetch(buildApiUrl(endpoint), {
                    headers: {
                        ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    },
                    signal: controller.signal,
                })

                if (!response.ok) {
                    throw new Error(`Khong the tai tai lieu: ${response.status}`)
                }

                const contentType = response.headers.get('content-type') || ''
                const filename = getFilenameFromContentDisposition(response.headers.get('content-disposition'))
                const resolvedTitle = filename || title
                const resolvedKind = classifyFileType(payload.type, resolvedTitle, contentType)
                if (resolvedKind === 'unsupported') {
                    throw new Error('Dinh dang tai lieu nay chua duoc ho tro xem truc tiep')
                }

                if (resolvedKind === 'word') {
                    if (!payload.document_id) {
                        throw new Error('Can document_id de xem preview Word/TXT/Markdown')
                    }

                    setViewer({
                        kind: 'word',
                        fileUrl: `/documents/${payload.document_id}/preview`,
                        fileType: payload.type || contentType || getFileExtension(resolvedTitle) || 'text',
                    })
                    return
                }

                const blob = await response.blob()
                objectUrl = URL.createObjectURL(blob)
                setViewer({
                    kind: resolvedKind,
                    fileUrl: objectUrl,
                    fileType: payload.type || contentType || getFileExtension(resolvedTitle),
                })
            } catch (err) {
                if ((err as Error).name !== 'AbortError') {
                    setError(err instanceof Error ? err.message : 'Khong the mo nguon')
                }
            }
        }

        loadSource()

        return () => {
            controller.abort()
            if (objectUrl) URL.revokeObjectURL(objectUrl)
        }
    }, [payload.document_id, payload.type, payload.url, title])

    return (
        <div className="flex h-screen flex-col bg-slate-100">
            <header className="flex items-center justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
                <div className="min-w-0">
                    <h1 className="truncate text-base font-bold text-slate-900">{title}</h1>
                    <p className="mt-1 text-xs font-medium text-slate-500">
                        {getViewerLabel(viewer?.kind || guessedKind)}
                        {(viewer?.kind || guessedKind) === 'pdf' && ` - Trang ${initialPage || 1}${pageCount ? ` / ${pageCount}` : ''}`}
                        {targetLabel && <span className="ml-2 text-slate-600">Nguon: {targetLabel}</span>}
                        {searchDebug ? (
                            <span className="ml-2 text-green-600">
                                Tim: {searchDebug.source} ({searchDebug.len} ky tu)
                            </span>
                        ) : (
                            <span className="ml-2 text-red-500">Khong co noi dung tim kiem</span>
                        )}
                    </p>
                </div>
                <button
                    type="button"
                    onClick={() => window.close()}
                    className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                >
                    Dong
                </button>
            </header>

            <main className="min-h-0 flex-1">
                {error && (
                    <div className="flex h-full items-center justify-center p-8 text-center text-sm font-medium text-red-500">
                        {error}
                    </div>
                )}

                {!error && !viewer && (
                    <div className="flex h-full items-center justify-center p-8 text-sm font-medium text-slate-500">
                        Dang tai tai lieu...
                    </div>
                )}

                {!error && viewer?.kind === 'pdf' && (
                    <PDFViewer
                        fileUrl={viewer.fileUrl}
                        initialPage={initialPage}
                        searchText={searchText}
                        chunkText={chunkText}
                        answerContext={answerContext}
                        citationTarget={citationTarget}
                        onLoadSuccess={setPageCount}
                        onLoadError={(err) => setError(err.message)}
                    />
                )}

                {!error && viewer?.kind === 'word' && (
                    <WordViewer
                        fileUrl={viewer.fileUrl}
                        searchText={searchText}
                        chunkText={chunkText}
                        answerContext={answerContext}
                        citationTarget={citationTarget}
                        onLoadSuccess={() => setPageCount(0)}
                        onLoadError={(err) => setError(err.message)}
                    />
                )}

                {!error && viewer?.kind === 'excel' && (
                    <ExcelViewer
                        fileUrl={viewer.fileUrl}
                        searchText={searchText}
                        onLoadSuccess={() => setPageCount(0)}
                        onLoadError={(err) => setError(err.message)}
                    />
                )}

                {!error && viewer?.kind === 'image' && (
                    <div className="flex h-full items-center justify-center overflow-auto bg-slate-100 p-6">
                        <img src={viewer.fileUrl} alt={title} className="max-h-full max-w-full object-contain" />
                    </div>
                )}
            </main>
        </div>
    )
}

export default function CitationViewerPage() {
    return (
        <Suspense fallback={<div className="p-8 text-sm text-slate-500">Dang tai...</div>}>
            <CitationViewerContent />
        </Suspense>
    )
}
