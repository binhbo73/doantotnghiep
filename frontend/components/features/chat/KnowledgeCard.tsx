'use client'

import React, { useEffect, useState } from 'react'
import {
    AlertTriangle,
    CheckCircle2,
    ExternalLink,
    File,
    FileText,
    Image as ImageIcon,
    ShieldCheck,
} from 'lucide-react'
import { buildApiUrl } from '@/config/api'
import { getAuthToken } from '@/services/auth'
import { logger } from '@/services/logger'
import type { CitationAttribution } from './ChatMessages'

interface Citation {
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
    asset_id?: string
    asset_caption?: string
    asset_image_path?: string
    asset_page_number?: number | string
    asset_sheet_name?: string
    asset_anchor_cell?: string
    asset?: {
        id: string
        image_url?: string | null
        thumbnail_url?: string | null
        caption?: string | null
        page_number?: number | null
        sheet_name?: string | null
        anchor_cell?: string | null
    }
}

interface KnowledgeCardProps {
    citations?: Citation[]
    grounding?: {
        grounded?: boolean
        grounding_score?: number
        citation_coverage?: number
        avg_similarity?: number
        revised?: boolean
        warning_visible?: boolean
    }
    factAttribution?: CitationAttribution[]
    isLoading?: boolean
    onCitationClick?: (citation: Citation) => void
}

const ICON_MAP: Record<string, React.ReactNode> = {
    pdf: <FileText size={16} className="shrink-0 text-orange-500" />,
    document: <File size={16} className="shrink-0 text-orange-500" />,
    article: <FileText size={16} className="shrink-0 text-orange-500" />,
    asset: <ImageIcon size={16} className="shrink-0 text-cyan-500" />,
}

const getCitationKey = (citation: Citation, index: number) => [
    citation.document_id || 'doc',
    citation.asset_id || citation.chunk_id || 'chunk',
    citation.id || citation.number || 'source',
    index,
].join('-')

const formatPercent = (value?: number) => {
    if (typeof value !== 'number' || Number.isNaN(value)) return null
    const normalized = value <= 1 ? value * 100 : value
    return `${Math.max(0, Math.min(100, Math.round(normalized)))}%`
}

const getAssetThumbnailEndpoint = (citation: Citation) => {
    const assetId = citation.asset_id || citation.asset?.id
    if (!assetId) return null
    const endpoint = citation.asset?.thumbnail_url || `/assets/${assetId}/thumbnail`
    return endpoint.startsWith('/api/v1/') ? endpoint.slice('/api/v1'.length) : endpoint
}

const getAssetCaption = (citation: Citation) => {
    return (citation.asset_caption || citation.asset?.caption || citation.description || 'Hinh anh trong tai lieu')
        .replace(/^\s*\d+\.\s*Loai anh\s*:\s*/i, '')
        .replace(/\b\d+\.\s*Mo ta noi dung\s*THUC TE\s*:\s*/i, '')
        .replace(/\b\d+\.\s*Chu y huong chu\s*:[^.?!]*(?:[.?!]|$)/gi, ' ')
        .replace(/\b\d+\.\s*Tuyet doi khong bia dat[^.?!]*(?:[.?!]|$)/gi, ' ')
        .replace(/\s+/g, ' ')
        .trim()
}

const getAssetLocation = (citation: Citation) => {
    const parts: string[] = []
    const sheet = citation.asset_sheet_name || citation.asset?.sheet_name
    const cell = citation.asset_anchor_cell || citation.asset?.anchor_cell
    const page = citation.asset_page_number || citation.asset?.page_number || citation.page
    if (sheet) parts.push(`Sheet ${sheet}`)
    if (cell) parts.push(`cell ${cell}`)
    if (page) parts.push(`Trang ${page}`)
    return parts.join(' · ')
}

const getCitationMeta = (citation: Citation) => {
    const parts: string[] = []

    if (citation.type === 'asset') {
        const location = getAssetLocation(citation)
        if (location) parts.push(location)
    } else {
        if (citation.page) parts.push(`Trang ${citation.page}`)
        if (citation.line_start) {
            parts.push(
                citation.line_end && citation.line_end !== citation.line_start
                    ? `dong ${citation.line_start}-${citation.line_end}`
                    : `dong ${citation.line_start}`
            )
        }
        if (citation.row_start) {
            parts.push(
                citation.row_end && citation.row_end !== citation.row_start
                    ? `row ${citation.row_start}-${citation.row_end}`
                    : `row ${citation.row_start}`
            )
        }
        if (typeof citation.chunk_index === 'number') parts.push(`chunk ${citation.chunk_index}`)
    }

    return parts.join(' · ')
}

const getCitationExcerpt = (citation: Citation) => (
    citation.answer_context ||
    citation.excerpt ||
    citation.description ||
    citation.source ||
    ''
).trim()

function AuthenticatedAssetImage({ citation, className = '' }: { citation: Citation; className?: string }) {
    const endpoint = getAssetThumbnailEndpoint(citation)
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
                if (!response.ok) throw new Error(`Cannot load asset thumbnail: ${response.status}`)
                const blob = await response.blob()
                objectUrl = URL.createObjectURL(blob)
                if (!cancelled) setSrc(objectUrl)
            } catch (err) {
                if (!cancelled) {
                    logger.error('Failed to load asset thumbnail', err)
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
            <div className={`flex items-center justify-center bg-cyan-50 text-cyan-600 dark:bg-cyan-950/30 ${className}`}>
                <ImageIcon size={18} />
            </div>
        )
    }

    if (!src) return <div className={`animate-pulse bg-slate-200 dark:bg-slate-700 ${className}`} />

    return <img src={src} alt={getAssetCaption(citation)} className={`object-cover ${className}`} />
}

export const KnowledgeCard: React.FC<KnowledgeCardProps> = ({
    citations = [],
    grounding,
    factAttribution = [],
    isLoading = false,
    onCitationClick,
}) => {
    if (!citations.length && !isLoading && !grounding) return null

    const isHiddenContentForCitation = (citation: Citation) => {
        const candidates = [citation.chunk_index, citation.chunk_id, citation.id, citation.number]
        return candidates.some((v) => String(v) === '191')
    }

    const uniqueCitations = citations.filter((citation, index, list) => {
        const key = [
            citation.document_id || citation.title,
            citation.page || '',
            citation.asset_id || citation.chunk_id || citation.excerpt || citation.description || '',
        ].join('|')

        return list.findIndex((item) => {
            const itemKey = [
                item.document_id || item.title,
                item.page || '',
                item.asset_id || item.chunk_id || item.excerpt || item.description || '',
            ].join('|')
            return itemKey === key
        }) === index
    })

    const groundingPercent = formatPercent(grounding?.grounding_score)
    const coveragePercent = formatPercent(grounding?.citation_coverage)
    const topClaims = factAttribution.slice(0, 4)

    return (
        <div className="mt-6 border-t border-outline-variant/20 pt-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <div>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                        Nguồn tham khảo ({uniqueCitations.length})
                    </p>
                </div>


            </div>



            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {isLoading ? (
                    <>
                        {[1, 2].map((i) => (
                            <div key={i} className="h-28 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-700" />
                        ))}
                    </>
                ) : (
                    uniqueCitations.map((citation, index) => {


                        const excerpt = getCitationExcerpt(citation)
                        const meta = getCitationMeta(citation)
                        const missingFacts = citation.missing_facts || []
                        const hideContent = isHiddenContentForCitation(citation)

                        const cardClass = hideContent
                            ? 'group flex items-center gap-3 rounded-xl border border-outline-variant/10 bg-white/60 p-2 text-left transition-all hover:border-primary/30 hover:bg-primary/5 dark:border-slate-700/50 dark:bg-slate-800/50 dark:hover:border-primary/30 dark:hover:bg-primary/5'
                            : 'group flex min-h-36 cursor-pointer gap-3 rounded-xl border border-outline-variant/10 bg-white/60 p-3 text-left transition-all hover:border-primary/30 hover:bg-primary/5 dark:border-slate-700/50 dark:bg-slate-800/50 dark:hover:border-primary/30 dark:hover:bg-primary/5'

                        return (
                            <button
                                key={getCitationKey(citation, index)}
                                onClick={() => onCitationClick?.(citation)}
                                className={cardClass}
                            >
                                {citation.type === 'asset' ? (
                                    hideContent ? (
                                        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-cyan-50 dark:bg-cyan-950/30">
                                            {ICON_MAP.asset}
                                        </div>
                                    ) : (
                                        <AuthenticatedAssetImage citation={citation} className="h-12 w-12 shrink-0 rounded-lg border border-slate-200 dark:border-slate-700" />
                                    )
                                ) : (
                                    <div className={`${hideContent ? 'mt-0 flex h-6 w-6' : 'mt-0.5 flex h-8 w-8'} shrink-0 items-center justify-center rounded-lg bg-orange-50 dark:bg-orange-950/30`}>
                                        {ICON_MAP[citation.type || 'document'] || ICON_MAP.document}
                                    </div>
                                )}

                                <div className={`min-w-0 flex-1 ${hideContent ? 'py-0' : ''}`}>
                                    <div className="flex items-center justify-between gap-2">
                                        <p className={`${hideContent ? 'text-sm font-semibold' : 'line-clamp-2 text-xs font-bold'} text-on-surface transition-colors group-hover:text-primary dark:text-slate-100`}>
                                            [{citation.number || index + 1}] {citation.type === 'asset' ? getAssetCaption(citation) : citation.title}
                                        </p>
                                        <ExternalLink size={14} className={`${hideContent ? 'mt-0' : 'mt-0.5'} shrink-0 text-slate-400 opacity-0 transition-opacity group-hover:opacity-100 dark:text-slate-500`} />
                                    </div>



                                    {!hideContent && excerpt && (
                                        <p className="mt-2 line-clamp-3 text-[11px] leading-5 text-slate-600 dark:text-slate-300">
                                            {excerpt}
                                        </p>
                                    )}
                                </div>
                            </button>
                        )
                    })
                )}
            </div>


        </div>
    )
}
