'use client'

import React, { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { formatRelativeTime, formatAbsoluteShort } from '@/lib/time'
import { Zap, Star, Copy, Share2, ExternalLink, LoaderCircle } from 'lucide-react'
import { KnowledgeCard } from './KnowledgeCard'
import { useFeedback } from '@/hooks/useFeedback'
import { useToast } from '@/hooks/useToast'
import { buildApiUrl } from '@/config/api'
import { getAuthToken } from '@/services/auth'
import { logger } from '@/services/logger'

export interface Message {
    id: string
    role: 'user' | 'assistant'
    content: string
    citations?: {
        id: string
        number?: number | string
        title: string
        source_label?: string
        description?: string
        answer_context?: string
        excerpt?: string
        page?: string | number
        chunk_index?: number
        line_start?: number
        line_end?: number
        row_start?: number
        row_end?: number
        start_char?: number
        end_char?: number
        document_id?: string
        chunk_id?: string
        source?: string
        score?: number
        confidence?: number
        grounding_score?: number
        overlap_score?: number
        retrieval_score?: number
        critical_facts?: string[]
        matched_facts?: string[]
        missing_facts?: string[]
        url?: string
        type?: string
        document_title?: string
        document_file_type?: string
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
            id: string
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
    }[]
    grounding?: {
        grounded?: boolean
        grounding_score?: number
        citation_coverage?: number
        avg_similarity?: number
        revised?: boolean
        warning_visible?: boolean
        ungrounded_claims?: unknown[]
        exact_unsupported_claims?: unknown[]
        claims?: CitationAttribution[]
    }
    factAttribution?: CitationAttribution[]
    timestamp?: Date
    isLoading?: boolean
    processingStatus?: string
}

type Citation = NonNullable<Message['citations']>[number]

export interface CitationAttribution {
    claim_index?: number
    claim?: string
    citation_numbers?: Array<number | string>
    best_citation?: number | string | null
    document_id?: string
    chunk_id?: string
    page?: string | number | null
    grounded?: boolean
    grounding_score?: number
    confidence?: number
    matched_facts?: string[]
    missing_facts?: string[]
}

type MessageContentBlock =
    | { type: 'text'; content: string }
    | { type: 'table'; headers: string[]; rows: string[][] }

const normalizeApiEndpoint = (endpoint?: string | null) => {
    if (!endpoint) return ''
    return endpoint.startsWith('/api/v1/') ? endpoint.slice('/api/v1'.length) : endpoint
}

const getAssetId = (citation: Citation) => citation.asset_id || citation.asset?.id

const getAssetImageEndpoint = (citation: Citation) => {
    const assetId = getAssetId(citation)
    if (assetId) return `/assets/${assetId}/image`
    return normalizeApiEndpoint(citation.asset?.image_url)
}

const getAssetThumbnailEndpoint = (citation: Citation) => {
    const assetId = getAssetId(citation)
    if (assetId) return `/assets/${assetId}/thumbnail`
    return normalizeApiEndpoint(citation.asset?.thumbnail_url)
}

const cleanAssetCaption = (value?: string | null) => {
    return (value || '')
        .replace(/^\s*\d+\.\s*Loại ảnh\s*:\s*/i, '')
        .replace(/\b\d+\.\s*Mô tả nội dung\s*THỰC TẾ\s*:\s*/i, '')
        .replace(/\b\d+\.\s*Chú ý hướng chữ\s*:[^.?!]*(?:[.?!]|$)/gi, ' ')
        .replace(/\b\d+\.\s*Tuyệt đối không bịa đặt[^.?!]*(?:[.?!]|$)/gi, ' ')
        .replace(/\s+/g, ' ')
        .trim()
}

const getAssetCaption = (citation: Citation) => (
    cleanAssetCaption(citation.asset_caption || citation.asset?.caption || citation.description || citation.title) || 'Ảnh minh chứng'
)

const getAssetLocation = (citation: Citation) => {
    const parts: string[] = []
    const sheet = citation.asset_sheet_name || citation.asset?.sheet_name
    const cell = citation.asset_anchor_cell || citation.asset?.anchor_cell
    const page = citation.asset_page_number || citation.asset?.page_number || citation.page
    if (sheet) parts.push(`Sheet ${sheet}`)
    if (cell) parts.push(`cell ${cell}`)
    if (page) parts.push(`Trang ${page}`)
    return parts.join(', ')
}

const getCitationNumber = (citation: Citation, index: number) => String(citation.number || citation.id || index + 1)

const getReferencedCitationNumbers = (content: string) => {
    const refs = new Set<string>()
    for (const match of content.matchAll(/\[(\d{1,3})\]/g)) {
        refs.add(match[1])
    }
    return refs
}

const getVisibleCitations = (content: string, citations: Citation[] = []) => {
    const refs = getReferencedCitationNumbers(content)
    if (!refs.size) return citations
    return citations.filter((citation, index) => refs.has(getCitationNumber(citation, index)))
}

const getCitationMeta = (citation: Citation) => {
    const parts: string[] = []
    if (citation.type === 'asset') {
        if (citation.asset_sheet_name || citation.asset?.sheet_name) {
            parts.push(`Sheet ${citation.asset_sheet_name || citation.asset?.sheet_name}`)
        }
        if (citation.asset_anchor_cell || citation.asset?.anchor_cell) {
            parts.push(`cell ${citation.asset_anchor_cell || citation.asset?.anchor_cell}`)
        }
        if (citation.asset_page_number || citation.asset?.page_number) {
            parts.push(`Trang ${citation.asset_page_number || citation.asset?.page_number}`)
        }
        return parts.join(', ')
    }
    if (citation.page) parts.push(`Trang ${citation.page}`)
    if (citation.line_start) {
        parts.push(citation.line_end && citation.line_end !== citation.line_start ? `dong ${citation.line_start}-${citation.line_end}` : `dong ${citation.line_start}`)
    } else if (typeof citation.chunk_index === 'number') {
        parts.push(`chunk ${citation.chunk_index}`)
    } else if (citation.start_char || citation.end_char) {
        parts.push(`ky tu ${citation.start_char || 0}-${citation.end_char || ''}`)
    }
    return parts.join(', ')
}

const isMarkdownTableSeparator = (line: string) => {
    const trimmed = line.trim()
    if (!trimmed) return false

    return /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(trimmed)
}

const splitMarkdownTableRow = (line: string) => {
    const trimmed = line.trim().replace(/^\|/, '').replace(/\|$/, '')
    return trimmed.split('|').map((cell) => cell.trim())
}

const renderTableCellContent = (cell: string) => {
    const parts = cell.split(/(?:<br\s*\/?>|&lt;br\s*\/?&gt;)/gi)
    if (parts.length === 1) return cell

    return parts.map((part, index) => (
        <React.Fragment key={`${part}-${index}`}>
            {index > 0 && <br />}
            {part}
        </React.Fragment>
    ))
}

const parseMessageContentBlocks = (content: string): MessageContentBlock[] => {
    const lines = content.replace(/\r\n/g, '\n').split('\n')
    const blocks: MessageContentBlock[] = []
    let index = 0

    while (index < lines.length) {
        if (!lines[index].trim()) {
            index += 1
            continue
        }

        const looksLikeTable =
            index + 1 < lines.length &&
            lines[index].includes('|') &&
            isMarkdownTableSeparator(lines[index + 1])

        if (looksLikeTable) {
            const headers = splitMarkdownTableRow(lines[index])
            const rows: string[][] = []
            index += 2

            while (index < lines.length && lines[index].trim() && lines[index].includes('|')) {
                rows.push(splitMarkdownTableRow(lines[index]))
                index += 1
            }

            blocks.push({ type: 'table', headers, rows })
            continue
        }

        const textLines: string[] = []
        while (index < lines.length && lines[index].trim()) {
            const isTableStart =
                index + 1 < lines.length &&
                lines[index].includes('|') &&
                isMarkdownTableSeparator(lines[index + 1])

            if (isTableStart) break
            textLines.push(lines[index])
            index += 1
        }

        if (textLines.length) {
            blocks.push({ type: 'text', content: textLines.join('\n') })
        }
    }

    return blocks
}

const SOURCE_LINE_PATTERN = /^\s*\[(?:Ngu[^\]:]*|Source):[^\]]+\](?:\s*\[\d{1,3}\])?\s*$/i
const SOURCE_TAIL_PATTERN = /\btrang\s*\d+\]?\s*\[\d{1,3}\]\s*$/i

const isCitationOnlyContext = (text?: string) => {
    const trimmed = (text || '').trim()
    if (!trimmed) return false
    return SOURCE_LINE_PATTERN.test(trimmed) || SOURCE_TAIL_PATTERN.test(trimmed)
}

const stripTrailingSourceLines = (text: string) => {
    const lines = text.replace(/\r/g, '').split('\n')

    while (lines.length && !lines[lines.length - 1].trim()) {
        lines.pop()
    }

    while (lines.length) {
        const tail = lines[lines.length - 1].trim()
        if (!SOURCE_LINE_PATTERN.test(tail) && !SOURCE_TAIL_PATTERN.test(tail)) break

        lines.pop()
        while (lines.length && !lines[lines.length - 1].trim()) {
            lines.pop()
        }
    }

    return lines.join('\n').trim()
}

const openCitationSource = async (citation: Citation) => {
    if (citation.type === 'asset' || getAssetId(citation)) {
        openAssetSource(citation)
        return
    }

    if (!citation.document_id && !citation.url) return

    if (citation.document_id && typeof window !== 'undefined') {
        const key = `citation-source-${Date.now()}-${Math.random().toString(36).slice(2)}`
        sessionStorage.setItem(key, JSON.stringify(citation))
        window.open(`/dashboard/citation-viewer?key=${encodeURIComponent(key)}`, '_blank')
        return
    }

    const popup = window.open('about:blank', '_blank')
    const token = getAuthToken()
    const endpoint = citation.url || `/documents/${citation.document_id}/download`
    const response = await fetch(buildApiUrl(endpoint), {
        headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
    })

    if (!response.ok) {
        popup?.close()
        throw new Error(`Cannot open source: ${response.status}`)
    }

    const blob = await response.blob()
    const objectUrl = URL.createObjectURL(blob)
    const pageSuffix = citation.page && blob.type.includes('pdf') ? `#page=${citation.page}` : ''
    if (popup) {
        popup.location.href = `${objectUrl}${pageSuffix}`
    } else {
        window.open(`${objectUrl}${pageSuffix}`, '_blank', 'noopener,noreferrer')
    }
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
}

const openAssetSource = (citation: Citation) => {
    if (typeof window === 'undefined') return
    const assetId = getAssetId(citation)
    if (!assetId || !citation.document_id) return

    const key = `citation-source-${Date.now()}-${Math.random().toString(36).slice(2)}`
    sessionStorage.setItem(key, JSON.stringify({
        ...citation,
        title: citation.document_title || citation.source_label || citation.title,
        type: citation.document_file_type || undefined,
        viewer_mode: 'source',
        asset_id: assetId,
        asset: {
            ...(citation.asset || {}),
            id: assetId,
            image_url: `/api/v1/assets/${assetId}/image`,
            thumbnail_url: `/api/v1/assets/${assetId}/thumbnail`,
        },
    }))
    window.open(`/dashboard/citation-viewer?key=${encodeURIComponent(key)}`, '_blank')
}

const openAssetImage = (citation: Citation) => {
    if (typeof window === 'undefined') return
    const assetId = getAssetId(citation)
    if (!assetId) return

    const key = `citation-asset-${Date.now()}-${Math.random().toString(36).slice(2)}`
    sessionStorage.setItem(key, JSON.stringify({
        ...citation,
        type: 'asset',
        asset_id: assetId,
        asset: {
            ...(citation.asset || {}),
            id: assetId,
            image_url: `/api/v1/assets/${assetId}/image`,
            thumbnail_url: `/api/v1/assets/${assetId}/thumbnail`,
        },
    }))
    window.open(`/dashboard/citation-viewer?key=${encodeURIComponent(key)}`, '_blank')
}

const getCitationAnswerContext = (content: string, citation: Citation, index: number) => {
    const number = getCitationNumber(citation, index).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const sourcePattern = new RegExp(`(?:\\[(?:Ngu[^\\]:]*|Source):[^\\]]+\\]\\s*)?\\[${number}\\]`, 'i')
    const match = sourcePattern.exec(content)
    if (!match) return ''

    const before = stripTrailingSourceLines(
        content.slice(0, match.index).replace(/\[(?:Ngu[^\]:]*|Source):[^\]]+\]\s*$/i, '')
    )
    const sourceText = before
    const paragraphParts = sourceText.split(/\n\s*\n/).map((part) => part.trim()).filter(Boolean)
    const lastParagraph = paragraphParts[paragraphParts.length - 1] || sourceText

    const lines = lastParagraph.split('\n').map((line) => line.trim()).filter(Boolean)
    if (lines.length > 1) {
        const selected: string[] = []
        for (let lineIndex = lines.length - 1; lineIndex >= 0; lineIndex -= 1) {
            const line = lines[lineIndex]
            selected.unshift(line)
            const selectedText = selected.join('\n')
            if (line.endsWith(':') || selected.length >= 5 || selectedText.length >= 520) break
        }
        return selected.join('\n').trim()
    }

    const sentenceMatches = Array.from(lastParagraph.matchAll(/[^.!?\n]+[.!?]?/g)).map((item) => item[0].trim()).filter(Boolean)
    const lastSentence = sentenceMatches[sentenceMatches.length - 1] || lastParagraph
    return lastSentence.slice(Math.max(0, lastSentence.length - 520)).trim()
}

const getUsableAnswerContext = (content: string, citation: Citation, index: number) => {
    const provided = (citation.answer_context || '').trim()
    if (provided && !isCitationOnlyContext(provided)) return provided
    return getCitationAnswerContext(content, citation, index)
}

const normalizeHighlightText = (value: string) =>
    value
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/\u0111/g, 'd')
        .replace(/\u0110/g, 'd')
        .toLowerCase()

const getPopupHighlightTerms = (citation: Citation) => {
    const reference = citation.answer_context || ''
    if (!reference) return []

    const stopwords = new Set([
        'nguon', 'trang', 'chunk', 'trong', 'nguoi', 'duoc', 'nhung', 'bang', 'cua', 'cho', 'voi',
        'this', 'that', 'from', 'with', 'your', 'have',
    ])

    return Array.from(new Set(
        normalizeHighlightText(reference)
            .split(/[^a-z0-9]+/i)
            .filter((word) => word.length >= 4 && !stopwords.has(word))
    )).slice(0, 18)
}

const getLineTermHits = (line: string, terms: string[]) => {
    const normalizedLine = normalizeHighlightText(line)
    if (!normalizedLine || /^[-\s_]+$/.test(normalizedLine) || normalizedLine.includes('image image')) {
        return 0
    }

    return terms.filter((term) => normalizedLine.includes(term)).length
}

const shouldHighlightPopupLine = (line: string, citation: Citation) => {
    const terms = getPopupHighlightTerms(citation)
    if (!terms.length) return false

    return getLineTermHits(line, terms) >= 2
}

const renderHighlightedExcerpt = (text: string, citation: Citation) => {
    const terms = getPopupHighlightTerms(citation)
    if (!terms.length || !text) return text

    const escapedTerms = terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    const pattern = new RegExp(`(${escapedTerms.join('|')})`, 'gi')
    const nodes: React.ReactNode[] = []
    let lastIndex = 0

    const renderInlineHighlights = (line: string, keyPrefix: string) => {
        const inlineNodes: React.ReactNode[] = []
        let inlineLastIndex = 0

        line.replace(pattern, (match, _term, offset) => {
            if (offset > inlineLastIndex) {
                inlineNodes.push(<React.Fragment key={`${keyPrefix}-plain-${inlineLastIndex}`}>{line.slice(inlineLastIndex, offset)}</React.Fragment>)
            }
            inlineNodes.push(
                <mark key={`${keyPrefix}-mark-${offset}`} className="rounded-sm bg-amber-200/80 px-0.5 font-semibold text-slate-950">
                    {match}
                </mark>
            )
            inlineLastIndex = offset + match.length
            return match
        })

        if (inlineLastIndex < line.length) {
            inlineNodes.push(<React.Fragment key={`${keyPrefix}-tail-${inlineLastIndex}`}>{line.slice(inlineLastIndex)}</React.Fragment>)
        }

        return inlineNodes
    }

    const lines = text.split(/(\n)/)
    if (lines.length > 1) {
        return lines.map((line, index) => {
            if (line === '\n') return <React.Fragment key={`nl-${index}`}>{line}</React.Fragment>

            if (shouldHighlightPopupLine(line, citation)) {
                return (
                    <mark key={`line-${index}`} className="rounded-md bg-amber-200/80 px-1 py-0.5 font-semibold text-slate-950">
                        {line}
                    </mark>
                )
            }

            if (getLineTermHits(line, terms) >= 2) {
                return <React.Fragment key={`line-${index}`}>{renderInlineHighlights(line, `line-${index}`)}</React.Fragment>
            }

            return <React.Fragment key={`line-${index}`}>{line}</React.Fragment>
        })
    }

    text.replace(pattern, (match, _term, offset) => {
        if (offset > lastIndex) {
            nodes.push(<React.Fragment key={`plain-${lastIndex}`}>{text.slice(lastIndex, offset)}</React.Fragment>)
        }
        nodes.push(
            <mark key={`mark-${offset}`} className="rounded-sm bg-amber-200/80 px-0.5 font-semibold text-slate-950">
                {match}
            </mark>
        )
        lastIndex = offset + match.length
        return match
    })

    if (lastIndex < text.length) {
        nodes.push(<React.Fragment key={`plain-tail-${lastIndex}`}>{text.slice(lastIndex)}</React.Fragment>)
    }

    return nodes
}

function AuthenticatedInlineAssetImage({ citation }: { citation: Citation }) {
    const endpoint = getAssetImageEndpoint(citation) || getAssetThumbnailEndpoint(citation)
    const [src, setSrc] = useState<string | null>(null)
    const [failed, setFailed] = useState(false)

    useEffect(() => {
        if (!endpoint) return
        let objectUrl: string | null = null
        let cancelled = false

        const load = async () => {
            try {
                const token = getAuthToken()
                const response = await fetch(buildApiUrl(endpoint), {
                    headers: {
                        ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    },
                })
                if (!response.ok) throw new Error(`Cannot load asset image: ${response.status}`)
                const blob = await response.blob()
                objectUrl = URL.createObjectURL(blob)
                if (!cancelled) setSrc(objectUrl)
            } catch (err) {
                if (!cancelled) {
                    logger.error('Failed to load inline asset image', err)
                    setFailed(true)
                }
            }
        }

        load()
        return () => {
            cancelled = true
            if (objectUrl) URL.revokeObjectURL(objectUrl)
        }
    }, [endpoint])

    if (!endpoint || failed) {
        return (
            <div className="flex min-h-40 items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 text-xs font-semibold text-slate-500 dark:border-slate-700 dark:bg-slate-900/50">
                Không tải được ảnh minh chứng
            </div>
        )
    }

    if (!src) {
        return <div className="h-56 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-700" />
    }

    return (
        <button
            type="button"
            onClick={() => openCitationSource(citation)}
            className="block w-full overflow-hidden rounded-lg border border-slate-200 bg-slate-50 text-left transition hover:border-primary/40 dark:border-slate-700 dark:bg-slate-900/40"
            title="Mo vi tri anh trong tai lieu goc"
        >
            <img
                src={src}
                alt={getAssetCaption(citation)}
                className="max-h-[520px] w-full object-contain"
            />
        </button>
    )
}

function InlineAssetGallery({ citations = [], messageContent = '' }: { citations?: Citation[], messageContent?: string }) {
    const visibleCitations = getVisibleCitations(messageContent, citations)
    const assets = visibleCitations
        .filter((citation) => {
            if (citation.type !== 'asset' && !getAssetId(citation)) return false;

            // Chỉ hiện ảnh nếu số thứ tự của nó (ví dụ [2]) có xuất hiện trong nội dung tin nhắn
            const citationNumber = String(citation.number || '');
            if (!citationNumber) return true; // Fallback nếu không có số

            const escapedNumber = citationNumber.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const pattern = new RegExp(`\\[${escapedNumber}\\]|\\]\\s*${escapedNumber}(?:[.\\s]|$)`, 'i');
            return pattern.test(messageContent);
        })
        .filter((citation, index, list) => {
            const key = getAssetId(citation) || citation.asset_image_path || citation.title
            return list.findIndex((item) => (getAssetId(item) || item.asset_image_path || item.title) === key) === index
        })

    if (!assets.length) return null

    return (
        <div className="not-prose space-y-3">
            {assets.map((citation, index) => (
                <figure key={`${getAssetId(citation) || citation.id || index}-inline`} className="space-y-2">
                    <AuthenticatedInlineAssetImage citation={citation} />
                </figure>
            ))}
        </div>
    )
}

interface ChatMessagesProps {
    messages?: Message[]
    isLoading?: boolean
    onCopy?: (content: string) => void
    onFeedback?: (messageId: string, rating: string, comment?: string) => Promise<void>
    userFeedback?: Map<string, string>
    feedbackLoading?: Map<string, boolean>
}

const ProcessingStatus = ({ status }: { status?: string }) => (
    <div className="not-prose rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-slate-700 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
        <div className="flex items-center gap-2 text-sm font-medium">
            <LoaderCircle size={16} className="shrink-0 animate-spin text-primary" />
            <span className="leading-5">{status || 'Đang xử lý yêu cầu...'}</span>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2">
            <span className="h-1.5 rounded-full bg-primary" />
            <span className="h-1.5 rounded-full bg-primary/50" />
            <span className="h-1.5 rounded-full bg-slate-200 dark:bg-slate-700" />
        </div>
    </div>
)

export const ChatMessages: React.FC<ChatMessagesProps> = ({
    messages = [],
    isLoading = false,
    onCopy,
    onFeedback,
    userFeedback: propUserFeedback,
    feedbackLoading: propFeedbackLoading,
}) => {
    const { submitFeedback, userFeedback: internalUserFeedback, loading: internalFeedbackLoading } = useFeedback()
    const userFeedback = propUserFeedback || internalUserFeedback
    const feedbackLoading = propFeedbackLoading || internalFeedbackLoading
    const { toast } = useToast()
    const [feedbackComments, setFeedbackComments] = useState<Map<string, string>>(new Map())
    const [showCommentBox, setShowCommentBox] = useState<string | null>(null)
    const [currentRating, setCurrentRating] = useState<string | null>(null)
    const [hoveredStar, setHoveredStar] = useState<{ [messageId: string]: number }>({})
    const hideCitationTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
    const scrollContainerRef = useRef<HTMLDivElement | null>(null)
    const bottomRef = useRef<HTMLDivElement | null>(null)
    const previousMessageCountRef = useRef(0)
    const previousLastMessageIdRef = useRef<string | null>(null)
    const hasInlineLoadingMessage = messages.some((message) => message.role === 'assistant' && message.isLoading)
    const [activeCitation, setActiveCitation] = useState<{
        key: string
        citation: Citation
        rect: DOMRect
    } | null>(null)

    const formatMessageTime = (timestamp?: Date) => {
        return formatRelativeTime(timestamp)
    }

    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

    const handleFeedback = async (messageId: string, rating: string, forceSubmit: boolean = false) => {
        // For star rating, we might want to show comment box immediately after rating
        if (!showCommentBox && !forceSubmit) {
            setShowCommentBox(messageId)
            setCurrentRating(rating)
            return
        }

        try {
            const comment = feedbackComments.get(messageId)?.trim()
            const normalizedRating: 'upvote' | 'downvote' = rating === 'downvote' ? 'downvote' : 'upvote'
            if (onFeedback) {
                await onFeedback(messageId, rating, comment)
            } else {
                await submitFeedback(messageId, normalizedRating, comment)
            }

            // Success!
            setShowCommentBox(null)
            setCurrentRating(null)
        } catch (err) {
            logger.error('Failed to submit feedback', err)
        }
    }

    const handleCopy = (content: string) => {
        navigator.clipboard.writeText(content)
        toast({
            title: 'Copied',
            description: 'Message copied to clipboard',
            type: 'success',
        })
        onCopy?.(content)
    }

    const handleOpenCitation = async (citation: Citation) => {
        try {
            await openCitationSource(citation)
        } catch (error) {
            logger.error('Failed to open citation source', error)
            toast({
                title: 'Khong the mo nguon',
                description: 'Vui long thu tai lai tai lieu hoac kiem tra quyen truy cap.',
                variant: 'destructive',
            })
        }
    }

    const cancelHideCitation = () => {
        if (hideCitationTimer.current) {
            clearTimeout(hideCitationTimer.current)
            hideCitationTimer.current = null
        }
    }

    const scheduleHideCitation = () => {
        cancelHideCitation()
        hideCitationTimer.current = setTimeout(() => {
            setActiveCitation(null)
        }, 400)
    }

    const showCitation = (key: string, citation: Citation, target: HTMLElement) => {
        cancelHideCitation()
        setActiveCitation({
            key,
            citation,
            rect: target.getBoundingClientRect(),
        })
    }

    // Close popup when clicking outside (but not on citation chips)
    useEffect(() => {
        if (!activeCitation) return
        const handleClickOutside = (e: MouseEvent) => {
            const target = e.target as HTMLElement
            if (!target.closest('.citation-popover') && !target.closest('.citation-chip')) {
                setActiveCitation(null)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [activeCitation])

    const renderCitationChip = (citation: Citation, index: number, occurrenceKey: string) => {
        const number = getCitationNumber(citation, index)

        return (
            <span key={occurrenceKey} className="relative mx-0.5 inline-flex align-baseline">
                <button
                    type="button"
                    onMouseEnter={(event) => showCitation(occurrenceKey, citation, event.currentTarget)}
                    onClick={(event) => {
                        event.preventDefault()
                        event.stopPropagation()
                        showCitation(occurrenceKey, citation, event.currentTarget)
                    }}
                    onFocus={(event) => showCitation(occurrenceKey, citation, event.currentTarget)}
                    onMouseLeave={scheduleHideCitation}
                    onBlur={scheduleHideCitation}
                    className="citation-chip inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-slate-900 px-1.5 text-[11px] font-semibold leading-none text-white transition-colors hover:bg-primary focus:outline-none focus:ring-2 focus:ring-primary/40 dark:bg-slate-200 dark:text-slate-900"
                    aria-label={`Nguon ${number}`}
                >
                    {number}
                </button>
            </span>
        )
    }

    const renderCitationPopover = () => {
        if (!activeCitation || typeof document === 'undefined') return null

        const { citation, rect } = activeCitation
        const meta = getCitationMeta(citation)
        const isAssetCitation = citation.type === 'asset' || Boolean(getAssetId(citation))
        const excerpt = citation.excerpt || citation.description || ''
        const answerCtx = citation.answer_context || ''
        const width = Math.min(540, Math.max(320, window.innerWidth - 32))
        const left = Math.min(Math.max(16, rect.left + rect.width / 2 - width / 2), window.innerWidth - width - 16)
        const estimatedHeight = 360
        const showBelow = rect.top < estimatedHeight + 24
        const top = showBelow ? rect.bottom + 10 : Math.max(16, rect.top - estimatedHeight - 10)

        return createPortal(
            <div
                className="citation-popover fixed z-[9999] rounded-xl border border-slate-200 bg-white text-left shadow-2xl dark:border-slate-700 dark:bg-slate-900"
                style={{ left, top, width, maxHeight: 'min(420px, calc(100vh - 32px))' }}
                onMouseEnter={cancelHideCitation}
                onMouseLeave={scheduleHideCitation}
            >
                <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 dark:border-slate-800">
                    <span className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate mr-2">{citation.title}</span>
                    <button
                        type="button"
                        onClick={() => setActiveCitation(null)}
                        className="shrink-0 rounded-full p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                        aria-label="Dong popup"
                    >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                    </button>
                </div>
                <div className="max-h-72 overflow-y-auto px-5 py-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
                    {meta && <div className="mb-3 text-xs font-semibold text-slate-500 dark:text-slate-400">{meta}</div>}
                    <div className="whitespace-pre-wrap">
                        {answerCtx && (
                            <div className="mb-3 p-2.5 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                                <div className="text-[10px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 mb-1">
                                    Câu trả lời
                                </div>
                                <div className="text-slate-900 dark:text-slate-100 font-semibold whitespace-pre-wrap leading-relaxed">
                                    {answerCtx}
                                </div>
                            </div>
                        )}
                        {excerpt ? renderHighlightedExcerpt(excerpt, citation) : 'Khong co doan trich hien thi.'}
                    </div>
                </div>
                <div className="border-t border-slate-100 px-5 py-4 dark:border-slate-800">
                    <button
                        type="button"
                        onClick={() => handleOpenCitation(citation)}
                        className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary hover:underline"
                    >
                        {isAssetCitation ? 'Xem trong file gốc' : 'Xem nguồn'}
                        <ExternalLink size={14} />
                    </button>
                </div>
            </div>,
            document.body
        )
    }

    const renderMessageContent = (content: string, citations: Citation[] = []) => {
        if (!citations.length) {
            // Strip raw citation markup when no citation data available
            return content.replace(/\[(?:Ngu[^\]:]*|Source):[^\]]+\]\s*\[\d{1,2}\]/gi, '').replace(/\[\d{1,2}\]/g, '').trim()
        }

        const citationMap = new Map<string, { citation: Citation; index: number }>()
        citations.forEach((citation, index) => {
            citationMap.set(getCitationNumber(citation, index), { citation, index })
        })

        const sourcePattern = /(\[(?:Ngu[^\]:]*|Source):[^\],]*(?:,\s*trang\s*(\d+))?[^\]]*\])(?:\s*\[(\d{1,2})\])?|\[(\d{1,2})\]/gi
        const nodes: React.ReactNode[] = []
        let lastIndex = 0
        let fallbackIndex = 0
        let occurrenceIndex = 0
        let match: RegExpExecArray | null

        const pushText = (text: string, key: string) => {
            if (text) {
                nodes.push(<React.Fragment key={key}>{text}</React.Fragment>)
            }
        }

        while ((match = sourcePattern.exec(content)) !== null) {
            if (match.index > lastIndex) {
                pushText(content.slice(lastIndex, match.index), `text-${lastIndex}-${match.index}`)
            }

            const longSourceText = match[1]
            const page = match[2]
            const explicitNumber = match[3] || match[4]
            let mapped = explicitNumber ? citationMap.get(explicitNumber) : undefined

            if (!mapped && !explicitNumber && page) {
                const pageMatchIndex = citations.findIndex((citation) => String(citation.page || '') === page)
                if (pageMatchIndex >= 0) {
                    mapped = { citation: citations[pageMatchIndex], index: pageMatchIndex }
                }
            }

            if (!mapped && !explicitNumber && citations[fallbackIndex]) {
                mapped = { citation: citations[fallbackIndex], index: fallbackIndex }
                fallbackIndex += 1
            }

            if (mapped) {
                const contextualCitation = {
                    ...mapped.citation,
                    answer_context: getUsableAnswerContext(content, mapped.citation, mapped.index),
                }
                const chipKey = `citation-${match.index}-${sourcePattern.lastIndex}-${mapped.index}-${occurrenceIndex}`
                nodes.push(renderCitationChip(contextualCitation, mapped.index, chipKey))
                occurrenceIndex += 1
            } else {
                pushText(match[0], `unmatched-${match.index}-${sourcePattern.lastIndex}`)
            }

            lastIndex = sourcePattern.lastIndex
        }

        if (lastIndex < content.length) {
            pushText(content.slice(lastIndex), `text-tail-${lastIndex}`)
        }

        return nodes
    }

    useEffect(() => {
        if (!messages.length) {
            previousMessageCountRef.current = 0
            previousLastMessageIdRef.current = null
            return
        }

        const container = scrollContainerRef.current
        const lastMessage = messages[messages.length - 1]
        const lastMessageId = lastMessage?.id || null
        const messageCountChanged = previousMessageCountRef.current !== messages.length
        const lastMessageChanged = previousLastMessageIdRef.current !== lastMessageId
        const isNearBottom = container
            ? container.scrollHeight - container.scrollTop - container.clientHeight < 180
            : true

        if (messageCountChanged || lastMessageChanged || isNearBottom) {
            window.requestAnimationFrame(() => {
                bottomRef.current?.scrollIntoView({
                    block: 'end',
                    behavior: messageCountChanged || lastMessageChanged ? 'auto' : 'smooth',
                })
            })
        }

        previousMessageCountRef.current = messages.length
        previousLastMessageIdRef.current = lastMessageId
    }, [messages])

    return (
        <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-6 md:p-12 space-y-10">
            {renderCitationPopover()}
            {messages.length === 0 && !isLoading && (
                <div className="flex flex-col items-center justify-center h-full text-center">
                    <Zap size={48} className="text-primary/20 mb-4" />
                    <h2 className="text-xl font-semibold text-slate-600 dark:text-slate-300 mb-2">
                        Bắt đầu một cuộc trò chuyện
                    </h2>
                    <p className="text-slate-500 dark:text-slate-400 max-w-sm">
                        Hỏi các câu hỏi về tài liệu và tri thức nội bộ của bạn. Tôi sẽ giúp bạn tìm câu trả lời.
                    </p>
                </div>
            )}

            {messages.map((message) => (
                <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} items-start gap-4`}>
                    {message.role === 'assistant' && (
                        <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shrink-0 shadow-lg shadow-primary/20">
                            <Zap size={20} className="text-on-primary" />
                        </div>
                    )}

                    <div className={`flex-1 ${message.role === 'user' ? 'max-w-lg' : 'max-w-5xl'}`}>
                        {message.role === 'user' ? (
                            <div className="space-y-2">
                                <div className="bg-primary-container text-on-primary-container p-4 rounded-2xl rounded-tr-none shadow-sm text-sm font-medium leading-relaxed">
                                    {message.content}
                                </div>
                                {message.timestamp && (
                                    <p className="px-1 text-[11px] text-slate-400 text-right" title={formatAbsoluteShort(message.timestamp)}>
                                        {formatMessageTime(message.timestamp)}
                                    </p>
                                )}
                            </div>
                        ) : (
                            <div className="glass-nugget p-6 rounded-2xl shadow-sm space-y-4 bg-white/70 dark:bg-slate-800/70 backdrop-blur-sm border border-outline-variant/10 dark:border-slate-700/20">
                                <div className="prose prose-sm dark:prose-invert max-w-none space-y-4">
                                    {message.isLoading && !message.content ? (
                                        <ProcessingStatus status={message.processingStatus} />
                                    ) : (
                                        <>
                                            {message.processingStatus && (
                                                <ProcessingStatus status={message.processingStatus} />
                                            )}
                                            {parseMessageContentBlocks(message.content).map((block, blockIndex) => {
                                                if (block.type === 'table') {
                                                    const maxColumns = Math.max(block.headers.length, ...block.rows.map((row) => row.length))
                                                    const normalizedHeaders = [...block.headers, ...Array(Math.max(0, maxColumns - block.headers.length)).fill('')]

                                                    return (
                                                        <div key={`table-${blockIndex}`} className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
                                                            <table className="min-w-full border-collapse text-sm text-slate-900 dark:text-slate-100">
                                                                <thead className="bg-slate-50 dark:bg-slate-800">
                                                                    <tr>
                                                                        {normalizedHeaders.map((header, headerIndex) => (
                                                                            <th
                                                                                key={`header-${blockIndex}-${headerIndex}`}
                                                                                className="border border-slate-200 dark:border-slate-700 px-3 py-2 text-left font-semibold align-top"
                                                                            >
                                                                                <span className="whitespace-pre-wrap">{header}</span>
                                                                            </th>
                                                                        ))}
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    {block.rows.map((row, rowIndex) => {
                                                                        const cells = [...row, ...Array(Math.max(0, maxColumns - row.length)).fill('')]

                                                                        return (
                                                                            <tr key={`row-${blockIndex}-${rowIndex}`} className="even:bg-slate-50/60 dark:even:bg-slate-800/50">
                                                                                {cells.map((cell, cellIndex) => (
                                                                                    <td
                                                                                        key={`cell-${blockIndex}-${rowIndex}-${cellIndex}`}
                                                                                        className="border border-slate-200 dark:border-slate-700 px-3 py-2 align-top leading-relaxed whitespace-pre-wrap"
                                                                                    >
                                                                                        {renderTableCellContent(cell)}
                                                                                    </td>
                                                                                ))}
                                                                            </tr>
                                                                        )
                                                                    })}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    )
                                                }

                                                return (
                                                    <p key={`text-${blockIndex}`} className="text-on-surface dark:text-slate-100 leading-relaxed whitespace-pre-wrap">
                                                        {renderMessageContent(block.content, message.citations)}
                                                    </p>
                                                )
                                            })}
                                        </>
                                    )}
                                </div>

                                {!message.isLoading && message.citations && (
                                    <InlineAssetGallery
                                        citations={message.citations}
                                        messageContent={message.content}
                                    />
                                )}

                                {message.timestamp && !message.isLoading && (
                                    <p className="text-[11px] text-slate-400" title={formatAbsoluteShort(message.timestamp)}>
                                        {formatMessageTime(message.timestamp)}
                                    </p>
                                )}

                                {message.citations && getVisibleCitations(message.content, message.citations).length > 0 && (
                                    <KnowledgeCard
                                        citations={getVisibleCitations(message.content, message.citations).map((citation, citationIndex) => ({
                                            ...citation,
                                            answer_context: getUsableAnswerContext(message.content, citation, citationIndex),
                                        }))}
                                        grounding={message.grounding}
                                        factAttribution={message.factAttribution || message.grounding?.claims || []}
                                        isLoading={message.isLoading}
                                        onCitationClick={handleOpenCitation}
                                    />
                                )}

                                {!message.isLoading && (
                                    <div className="space-y-3 pt-2">
                                        <div className="flex items-center justify-between">
                                            <div className="flex flex-col gap-3">
                                                <div className="flex items-center gap-1">
                                                    {[1, 2, 3, 4, 5].map((star) => {
                                                        const isSelected = (parseInt(userFeedback.get(message.id) || '0')) >= star || (parseInt(currentRating || '0')) >= star;
                                                        const isHovered = (hoveredStar[message.id] || 0) >= star;

                                                        return (
                                                            <button
                                                                key={star}
                                                                onMouseEnter={() => setHoveredStar(prev => ({ ...prev, [message.id]: star }))}
                                                                onMouseLeave={() => setHoveredStar(prev => ({ ...prev, [message.id]: 0 }))}
                                                                onClick={() => {
                                                                    if (!uuidRegex.test(message.id)) {
                                                                        toast({ title: 'Chờ lưu', description: 'Tin nhắn chưa được lưu trên máy chủ. Vui lòng đợi rồi thử lại.', type: 'info' })
                                                                        return
                                                                    }
                                                                    handleFeedback(message.id, star.toString())
                                                                }}
                                                                disabled={feedbackLoading.get(message.id) || !uuidRegex.test(message.id)}
                                                                className="p-1 transition-all transform hover:scale-110 active:scale-95 disabled:opacity-50"
                                                            >
                                                                <Star
                                                                    size={18}
                                                                    className={`${isHovered || isSelected
                                                                        ? 'text-amber-400 fill-amber-400'
                                                                        : 'text-slate-300 dark:text-slate-600 hover:text-amber-200'
                                                                        } transition-colors duration-200`}
                                                                />
                                                            </button>
                                                        )
                                                    })}
                                                    <span className="ml-2 text-[10px] text-slate-400 font-medium">
                                                        {userFeedback.get(message.id) ? 'Đã đánh giá' : 'Đánh giá câu trả lời này'}
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => handleCopy(message.content)}
                                                    className="p-2 text-slate-400 hover:text-primary transition-colors rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                                                    title="Copy message"
                                                >
                                                    <Copy size={16} />
                                                </button>
                                                <button
                                                    onClick={() => {
                                                        if (navigator.share) {
                                                            navigator.share({
                                                                title: 'AI Response',
                                                                text: message.content,
                                                                url: window.location.href,
                                                            })
                                                        } else {
                                                            toast({
                                                                title: 'Sharing not supported',
                                                                description: 'Your browser does not support native sharing.',
                                                                variant: 'destructive',
                                                            })
                                                        }
                                                    }}
                                                    className="p-2 text-slate-400 hover:text-primary transition-colors rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                                                    title="Share message"
                                                >
                                                    <Share2 size={16} />
                                                </button>
                                            </div>
                                        </div>

                                        {/* Feedback Comment Box */}
                                        {showCommentBox === message.id && (
                                            <div className="mt-3 p-3 bg-slate-100 dark:bg-slate-700 rounded-lg space-y-2">
                                                <textarea
                                                    value={feedbackComments.get(message.id) || ''}
                                                    onChange={(e) =>
                                                        setFeedbackComments((prev) => new Map(prev).set(message.id, e.target.value))
                                                    }
                                                    placeholder="Hãy cho chúng tôi biết lý do (tùy chọn)..."
                                                    maxLength={1000}
                                                    className="w-full p-3 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-rose-500/50 focus:border-rose-500/50 transition-all resize-none"
                                                    rows={3}
                                                />
                                                <div className="flex gap-2 justify-end">
                                                    <button
                                                        onClick={() => setShowCommentBox(null)}
                                                        className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                                                    >
                                                        Hủy
                                                    </button>
                                                    <button
                                                        onClick={() => {
                                                            if (!uuidRegex.test(message.id)) {
                                                                toast({ title: 'Chờ lưu', description: 'Tin nhắn chưa được lưu trên máy chủ. Vui lòng đợi rồi thử lại.', type: 'info' })
                                                                return
                                                            }
                                                            const rating = currentRating || userFeedback.get(message.id) || '5'
                                                            handleFeedback(message.id, rating, true)
                                                        }}
                                                        disabled={feedbackLoading.get(message.id) || !uuidRegex.test(message.id)}
                                                        className="px-4 py-1.5 text-xs font-semibold bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors shadow-sm shadow-amber-200 dark:shadow-none disabled:opacity-50"
                                                    >
                                                        {feedbackLoading.get(message.id) ? 'Đang gửi...' : 'Gửi đánh giá'}
                                                    </button>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {message.role === 'user' && (
                        <div className="w-8 h-8 rounded-lg bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center shrink-0">
                            <span className="text-orange-600 dark:text-orange-400 text-sm font-bold">A</span>
                        </div>
                    )}
                </div>
            ))}

            {isLoading && !hasInlineLoadingMessage && (
                <div className="flex justify-start items-center gap-4 opacity-50">
                    <div className="w-10 h-10 rounded-xl bg-slate-200 dark:bg-slate-700 animate-pulse" />
                    <div className="h-4 w-32 bg-slate-200 dark:bg-slate-700 rounded-full animate-pulse" />
                </div>
            )}
            <div ref={bottomRef} aria-hidden="true" />
        </div>
    )
}
