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
    viewer_mode?: 'asset' | 'source'
    asset_id?: string
    asset_caption?: string
    asset_image_path?: string
    asset_page_number?: number | string
    asset_sheet_name?: string
    asset_anchor_cell?: string
    asset_paragraph_index?: number | null
    asset_position_in_document?: Record<string, number> | null
    asset_context_text?: string
    asset?: {
        id?: string
        image_url?: string | null
        thumbnail_url?: string | null
        caption?: string | null
        page_number?: number | null
        sheet_name?: string | null
        anchor_cell?: string | null
        paragraph_index?: number | null
        position_in_document?: Record<string, number> | null
        context_text?: string | null
    }
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
    sheet_name?: string
    row_start?: number
    row_end?: number
    start_char?: number
    end_char?: number
    line_start?: number
    line_end?: number
}

type DocumentAssetSource = {
    id: string
    asset_type?: string | null
    page_number?: number | null
    sheet_name?: string | null
    anchor_cell?: string | null
    paragraph_index?: number | null
    position_in_document?: Record<string, number> | null
    context_text?: string | null
    caption?: string | null
    image_url?: string | null
    thumbnail_url?: string | null
}

type AssetImageHint = {
    id?: string
    pageNumber?: number
    sheetName?: string
    anchorCell?: string
    paragraphIndex?: number
    imageIndex?: number
    position?: Record<string, number>
    imageEndpoint?: string
    caption?: string
    contextText?: string
}

const getPositionNumber = (position: Record<string, number> | null | undefined, key: string) => {
    const value = position?.[key]
    return typeof value === 'number' && Number.isFinite(value) ? value : undefined
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

function isOfficeWordFile(type?: string, title?: string, contentType?: string): boolean {
    const normalizedType = (type || '').toLowerCase().trim()
    const normalizedContentType = (contentType || '').toLowerCase().trim()
    const extension = getFileExtension(title)
    const candidates = [normalizedType, normalizedContentType, extension].filter(Boolean)

    return candidates.some((value) => (
        ['doc', 'docx', '.doc', '.docx'].includes(value) ||
        value.includes('application/msword') ||
        value.includes('wordprocessingml.document')
    ))
}

function getViewerLabel(kind?: ViewerKind): string {
    switch (kind) {
        case 'pdf':
            return 'Tài liệu PDF'
        case 'word':
            return 'Tài liệu Word / văn bản'
        case 'excel':
            return 'Bảng tính Excel'
        case 'image':
            return 'Hình ảnh'
        default:
            return 'Tài liệu nguồn'
    }
}

function normalizeApiEndpoint(endpoint?: string | null): string {
    if (!endpoint) return ''
    return endpoint.startsWith('/api/v1/') ? endpoint.slice('/api/v1'.length) : endpoint
}

function CitationViewerContent() {
    const searchParams = useSearchParams()
    const [viewer, setViewer] = useState<ViewerState | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [pageCount, setPageCount] = useState(0)
    const [searchDebug, setSearchDebug] = useState<{ source: SearchTextSource, len: number, preview: string } | null>(null)
    const [chunkSource, setChunkSource] = useState<CitationChunkSource | null>(null)
    const [documentAssets, setDocumentAssets] = useState<DocumentAssetSource[]>([])
    const [isAssetsLoading, setIsAssetsLoading] = useState(true)

    const payload = useMemo<CitationViewerPayload>(() => {
        const storageKey = searchParams.get('key')
        if (storageKey && typeof window !== 'undefined') {
            try {
                const raw = sessionStorage.getItem(storageKey)
                console.log(`[CitationViewer] sessionStorage key=${storageKey}, raw payload:`, raw ? JSON.parse(raw) : 'NULL')
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

    const assetId = payload.asset_id || payload.asset?.id
    const hasAsset = payload.type === 'asset' || Boolean(assetId)
    const shouldOpenAssetImage = hasAsset && payload.viewer_mode === 'asset'

    console.log(`[CitationViewer] Payload analysis: document_id=${payload.document_id}, type=${payload.type}, asset_id=${assetId}, hasAsset=${hasAsset}, viewer_mode=${payload.viewer_mode}, shouldOpenAssetImage=${shouldOpenAssetImage}`)

    useEffect(() => {
        if (shouldOpenAssetImage || !payload.document_id || !payload.chunk_id) {
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
    }, [shouldOpenAssetImage, payload.document_id, payload.chunk_id])

    useEffect(() => {
        if (shouldOpenAssetImage || !payload.document_id) {
            setDocumentAssets([])
            setIsAssetsLoading(false)
            return
        }

        setIsAssetsLoading(true)
        const controller = new AbortController()
        const loadDocumentAssets = async () => {
            try {
                const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
                const response = await fetch(buildApiUrl(`/documents/${payload.document_id}/assets`), {
                    headers: {
                        ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    },
                    signal: controller.signal,
                })

                if (!response.ok) {
                    setDocumentAssets([])
                    return
                }

                const body = await response.json()
                const data = body?.data || body
                const assetsArray = Array.isArray(data) ? data : []
                console.log(`[CitationViewer] Loaded ${assetsArray.length} assets for document ${payload.document_id}:`)
                assetsArray.forEach((a, idx) => {
                    console.log(`  [${idx}] id=${a.id}, type=${a.asset_type}, page=${a.page_number}, sheet=${a.sheet_name}, anchor=${a.anchor_cell}, image_url=${a.image_url}`)
                })
                setDocumentAssets(assetsArray)
            } catch (err) {
                if ((err as Error).name !== 'AbortError') {
                    setDocumentAssets([])
                }
            } finally {
                setIsAssetsLoading(false)
            }
        }

        loadDocumentAssets()

        return () => controller.abort()
    }, [shouldOpenAssetImage, payload.document_id])

    const initialPage = Number(chunkSource?.page_number || payload.page || 1)
    const preferredCitationText = hasAsset
        ? (payload.asset_context_text || payload.asset?.context_text || payload.description || payload.excerpt || '')
        : (payload.excerpt || payload.description || '')
    const chunkSectionText = getPrimaryChunkSection(chunkSource?.content, preferredCitationText)
    // chunkSource.content thuong overlap voi chunk ke tiep, nen chi truyen section chinh
    // cua chunk xuong viewer. Excerpt/description/chunk moi la text goc trong tai lieu.
    // answer_context la cau tra loi cua LLM, chi dung doi chieu, khong lam neo chinh.
    const searchText = preferredCitationText || chunkSectionText || chunkSource?.content || payload.answer_context || ''
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
        const source: SearchTextSource = payload.excerpt ? 'excerpt' : payload.description ? 'description' : chunkText ? 'chunk' : payload.answer_context ? 'answer_context' : 'none'
        setSearchDebug(searchText ? {
            source,
            len: searchText.length,
            preview: searchText.substring(0, 150).replace(/\n/g, ' ')
        } : null)
    }, [searchText, chunkText, payload])
    const title = payload.title || payload.asset_caption || payload.asset?.caption || 'Tai lieu nguon'
    const guessedKind = shouldOpenAssetImage ? 'image' : classifyFileType(payload.type, title)
    const excelAssetImages = useMemo(() => {
        console.log(`[CitationViewer excelAssetImages] documentAssets:`, documentAssets)
        const mapped = documentAssets.map((item) => ({
            id: item.id,
            pageNumber: item.page_number || undefined,
            sheetName: item.sheet_name || undefined,
            anchorCell: item.anchor_cell || undefined,
            paragraphIndex: typeof item.paragraph_index === 'number' ? item.paragraph_index : undefined,
            imageIndex: getPositionNumber(item.position_in_document, 'image_index'),
            position: item.position_in_document || undefined,
            imageEndpoint: item.image_url ? normalizeApiEndpoint(item.image_url) : `/assets/${item.id}/image`,
            caption: item.caption || undefined,
            contextText: item.context_text || undefined,
        }))

        // If we have a payload asset but it's not in documentAssets, 
        // we already handle finding a replacement in currentAsset.
        // If NO documentAssets were loaded at all (e.g. error or empty), 
        // and loading is finished, then we fallback to the payload asset.
        if (!isAssetsLoading && mapped.length === 0 && hasAsset && assetId) {
            mapped.push({
                id: assetId,
                pageNumber: Number(payload.asset_page_number || payload.asset?.page_number || payload.page) || undefined,
                sheetName: payload.asset_sheet_name || payload.asset?.sheet_name || undefined,
                anchorCell: payload.asset_anchor_cell || payload.asset?.anchor_cell || undefined,
                paragraphIndex: typeof payload.asset_paragraph_index === 'number' ? payload.asset_paragraph_index : typeof payload.asset?.paragraph_index === 'number' ? payload.asset.paragraph_index : undefined,
                imageIndex: getPositionNumber(payload.asset_position_in_document || payload.asset?.position_in_document, 'image_index'),
                position: payload.asset_position_in_document || payload.asset?.position_in_document || undefined,
                imageEndpoint: `/assets/${assetId}/image`,
                caption: payload.asset_caption || payload.asset?.caption || payload.title,
                contextText: payload.asset_context_text || payload.asset?.context_text || undefined,
            })
        }

        return mapped
    }, [assetId, documentAssets, hasAsset, payload, isAssetsLoading])

    const currentAsset = useMemo(() => {
        if (!hasAsset || !assetId) return undefined

        // If still loading, we shouldn't prematurely resolve to the stale ID
        if (isAssetsLoading) return undefined

        // Try to find the actual asset from documentAssets first (more reliable IDs)
        const targetSheet = payload.asset_sheet_name || payload.asset?.sheet_name
        const targetAnchor = payload.asset_anchor_cell || payload.asset?.anchor_cell

        // Find if this specific assetId still exists in the document's assets
        const exactMatch = documentAssets.find(a => a.id === assetId)
        if (exactMatch) {
            return {
                id: exactMatch.id,
                pageNumber: exactMatch.page_number || undefined,
                sheetName: exactMatch.sheet_name || undefined,
                anchorCell: exactMatch.anchor_cell || undefined,
                paragraphIndex: typeof exactMatch.paragraph_index === 'number' ? exactMatch.paragraph_index : undefined,
                imageIndex: getPositionNumber(exactMatch.position_in_document, 'image_index'),
                position: exactMatch.position_in_document || undefined,
                imageEndpoint: exactMatch.image_url ? normalizeApiEndpoint(exactMatch.image_url) : `/assets/${exactMatch.id}/image`,
                caption: exactMatch.caption || undefined,
                contextText: exactMatch.context_text || undefined,
            }
        }

        // If not found by ID, try to find a replacement at the same sheet/cell
        if (targetSheet && targetAnchor) {
            const anchorMatch = documentAssets.find(a =>
                a.sheet_name === targetSheet &&
                a.anchor_cell === targetAnchor
            )
            if (anchorMatch) {
                console.log(`[CitationViewer] Found replacement for stale asset ${assetId} at ${targetSheet} ${targetAnchor}: ${anchorMatch.id}`)
                return {
                    id: anchorMatch.id,
                    pageNumber: anchorMatch.page_number || undefined,
                    sheetName: anchorMatch.sheet_name || undefined,
                    anchorCell: anchorMatch.anchor_cell || undefined,
                    paragraphIndex: typeof anchorMatch.paragraph_index === 'number' ? anchorMatch.paragraph_index : undefined,
                    imageIndex: getPositionNumber(anchorMatch.position_in_document, 'image_index'),
                    position: anchorMatch.position_in_document || undefined,
                    imageEndpoint: anchorMatch.image_url ? normalizeApiEndpoint(anchorMatch.image_url) : `/assets/${anchorMatch.id}/image`,
                    caption: anchorMatch.caption || undefined,
                    contextText: anchorMatch.context_text || undefined,
                }
            }
        }

        // Fallback to what we have (might 404 if stale)
        return {
            id: assetId,
            pageNumber: Number(payload.asset_page_number || payload.asset?.page_number || payload.page) || undefined,
            sheetName: targetSheet || undefined,
            anchorCell: targetAnchor || undefined,
            paragraphIndex: typeof payload.asset_paragraph_index === 'number' ? payload.asset_paragraph_index : typeof payload.asset?.paragraph_index === 'number' ? payload.asset.paragraph_index : undefined,
            imageIndex: getPositionNumber(payload.asset_position_in_document || payload.asset?.position_in_document, 'image_index'),
            position: payload.asset_position_in_document || payload.asset?.position_in_document || undefined,
            imageEndpoint: `/assets/${assetId}/image`,
            caption: payload.asset_caption || payload.asset?.caption || payload.title,
            contextText: payload.asset_context_text || payload.asset?.context_text || undefined,
        }
    }, [hasAsset, assetId, payload, documentAssets])

    // Derived asset ID to use for fetching (fixed if stale)
    const resolvedAssetId = currentAsset?.id || assetId
    const assetSearchText = currentAsset?.contextText || payload.asset_context_text || payload.asset?.context_text || searchText

    useEffect(() => {
        // Wait until assets are loaded before attempting to open an asset image
        if (shouldOpenAssetImage && isAssetsLoading) return

        let objectUrl = ''
        const controller = new AbortController()

        const loadSource = async () => {
            try {
                setError(null)
                setViewer(null)
                const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
                if (shouldOpenAssetImage) {
                    const assetEndpoint = resolvedAssetId ? `/assets/${resolvedAssetId}/image` : normalizeApiEndpoint(payload.asset?.image_url)
                    const fallbackEndpoint = normalizeApiEndpoint(payload.asset?.thumbnail_url) || (resolvedAssetId ? `/assets/${resolvedAssetId}/thumbnail` : '')
                    const endpoint = assetEndpoint || fallbackEndpoint
                    if (!endpoint) {
                        throw new Error('Khong co asset_id de mo anh minh chung')
                    }

                    const response = await fetch(buildApiUrl(endpoint), {
                        headers: {
                            ...(token ? { Authorization: `Bearer ${token}` } : {}),
                        },
                        signal: controller.signal,
                    })

                    if (!response.ok) {
                        throw new Error(`Khong the tai anh minh chung: ${response.status}`)
                    }

                    const blob = await response.blob()
                    objectUrl = URL.createObjectURL(blob)
                    setViewer({
                        kind: 'image',
                        fileUrl: objectUrl,
                        fileType: response.headers.get('content-type') || 'image',
                    })
                    return
                }

                const endpoint = payload.url || (payload.document_id ? `/documents/${payload.document_id}/download` : '')
                if (!endpoint) {
                    throw new Error('Khong co document_id de mo nguon')
                }

                const initialKind = classifyFileType(payload.type, title)

                if (initialKind === 'word' && payload.document_id && isOfficeWordFile(payload.type, title)) {
                    const response = await fetch(buildApiUrl(`/documents/${payload.document_id}/preview`), {
                        headers: {
                            ...(token ? { Authorization: `Bearer ${token}` } : {}),
                        },
                        signal: controller.signal,
                    })

                    if (!response.ok) {
                        throw new Error(`Khong the tai preview Word: ${response.status}`)
                    }

                    const blob = await response.blob()
                    objectUrl = URL.createObjectURL(blob)
                    setViewer({
                        kind: 'pdf',
                        fileUrl: objectUrl,
                        fileType: 'application/pdf',
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

                if (resolvedKind === 'word' && isOfficeWordFile(payload.type, resolvedTitle, contentType)) {
                    if (!payload.document_id) {
                        throw new Error('Can document_id de xem preview Word')
                    }

                    const previewResponse = await fetch(buildApiUrl(`/documents/${payload.document_id}/preview`), {
                        headers: {
                            ...(token ? { Authorization: `Bearer ${token}` } : {}),
                        },
                        signal: controller.signal,
                    })

                    if (!previewResponse.ok) {
                        throw new Error(`Khong the tai preview Word: ${previewResponse.status}`)
                    }

                    const previewBlob = await previewResponse.blob()
                    objectUrl = URL.createObjectURL(previewBlob)
                    setViewer({
                        kind: 'pdf',
                        fileUrl: objectUrl,
                        fileType: 'application/pdf',
                    })
                    return
                }

                if (resolvedKind === 'word') {
                    if (!payload.document_id) {
                        throw new Error('Can document_id de xem preview Word/TXT/Markdown')
                    }

                    setViewer({
                        kind: 'word',
                        fileUrl: `/documents/${payload.document_id}/preview?format=html`,
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
    }, [resolvedAssetId, shouldOpenAssetImage, payload, title, isAssetsLoading])

    return (
        <div className="flex h-screen flex-col bg-slate-100">
            <header className="flex items-center justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
                <div className="min-w-0">
                    <h1 className="truncate text-base font-bold text-slate-900">{title}</h1>
                    <p className="mt-1 text-xs font-medium text-slate-500">
                        {getViewerLabel(viewer?.kind || guessedKind)}
                        {hasAsset && (payload.asset_sheet_name || payload.asset?.sheet_name) && (
                            <span className="ml-2 text-slate-600">Sheet {payload.asset_sheet_name || payload.asset?.sheet_name}</span>
                        )}

                    </p>
                </div>
                <button
                    type="button"
                    onClick={() => window.close()}
                    className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                >
                    Đóng
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
                        Đang tải tài liệu...
                    </div>
                )}

                {!error && viewer?.kind === 'pdf' && (
                    <PDFViewer
                        fileUrl={viewer.fileUrl}
                        initialPage={initialPage}
                        searchText={searchText}
                        chunkText={chunkText}
                        answerContext={hasAsset ? '' : answerContext}
                        citationTarget={citationTarget}
                        assetImage={currentAsset}
                        onLoadSuccess={setPageCount}
                        onLoadError={(err) => setError(err.message)}
                    />
                )}

                {!error && viewer?.kind === 'word' && (
                    <WordViewer
                        fileUrl={viewer.fileUrl}
                        searchText={hasAsset ? assetSearchText : searchText}
                        chunkText={hasAsset ? '' : chunkText}
                        answerContext={hasAsset ? '' : answerContext}
                        citationTarget={citationTarget}
                        assetImage={currentAsset}
                        onLoadSuccess={() => setPageCount(0)}
                        onLoadError={(err) => setError(err.message)}
                    />
                )}

                {!error && viewer?.kind === 'excel' && (
                    <>
                        {console.log(`[CitationViewer] Rendering ExcelViewer with ${excelAssetImages.length} assetImages and currentAsset:`, currentAsset)}
                        {isAssetsLoading ? (
                            <div className="flex h-full items-center justify-center p-8 text-sm font-medium text-slate-500">
                                Dang dong bo hinh anh...
                            </div>
                        ) : (
                            <ExcelViewer
                                fileUrl={viewer.fileUrl}
                                searchText={searchText}
                                initialSheet={initialPage}
                                assetImage={currentAsset}
                                assetImages={excelAssetImages}
                                onLoadSuccess={() => setPageCount(0)}
                                onLoadError={(err) => setError(err.message)}
                            />
                        )}
                    </>
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
