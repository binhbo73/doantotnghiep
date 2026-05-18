'use client'

import React, { useEffect, useState } from 'react'
import { FileText, File, ExternalLink, Image as ImageIcon } from 'lucide-react'
import { buildApiUrl } from '@/config/api'

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
    start_char?: number
    end_char?: number
    document_id?: string
    chunk_id?: string
    source?: string
    score?: number
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
    isLoading?: boolean
    onCitationClick?: (citation: Citation) => void
}

const ICON_MAP: Record<string, React.ReactNode> = {
    pdf: <FileText size={16} className="text-orange-400 shrink-0" />,
    document: <File size={16} className="text-orange-400 shrink-0" />,
    article: <FileText size={16} className="text-orange-400 shrink-0" />,
    asset: <ImageIcon size={16} className="text-cyan-500 shrink-0" />,
}

const getCitationKey = (citation: Citation, index: number) => {
    return [
        citation.document_id || 'doc',
        citation.asset_id || citation.chunk_id || 'chunk',
        citation.id || citation.number || 'source',
        index,
    ].join('-')
}

const getAssetThumbnailEndpoint = (citation: Citation) => {
    const assetId = citation.asset_id || citation.asset?.id
    if (!assetId) return null
    const endpoint = citation.asset?.thumbnail_url || `/assets/${assetId}/thumbnail`
    return endpoint.startsWith('/api/v1/') ? endpoint.slice('/api/v1'.length) : endpoint
}

const getAssetCaption = (citation: Citation) => {
    return (citation.asset_caption || citation.asset?.caption || citation.description || 'Hình ảnh trong tài liệu')
        .replace(/^\s*\d+\.\s*Loại ảnh\s*:\s*/i, '')
        .replace(/\b\d+\.\s*Mô tả nội dung\s*THỰC TẾ\s*:\s*/i, '')
        .replace(/\b\d+\.\s*Chú ý hướng chữ\s*:[^.?!]*(?:[.?!]|$)/gi, ' ')
        .replace(/\b\d+\.\s*Tuyệt đối không bịa đặt[^.?!]*(?:[.?!]|$)/gi, ' ')
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
    return parts.join(', ')
}

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
                const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
                const response = await fetch(buildApiUrl(endpoint), {
                    headers: {
                        ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    },
                })
                if (!response.ok) throw new Error(`Cannot load asset thumbnail: ${response.status}`)
                const blob = await response.blob()
                objectUrl = URL.createObjectURL(blob)
                if (!cancelled) setSrc(objectUrl)
            } catch {
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
    isLoading = false,
    onCitationClick,
}) => {
    if (!citations.length && !isLoading) return null

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

    return (
        <div className="mt-6 pt-4 border-t border-outline-variant/20">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">
                Nguồn trích dẫn ({uniqueCitations.length})
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {isLoading ? (
                    <>
                        {[1, 2].map((i) => (
                            <div key={i} className="h-16 bg-slate-200 dark:bg-slate-700 rounded-xl animate-pulse" />
                        ))}
                    </>
                ) : (
                    uniqueCitations.map((citation, index) => (
                        <button
                            key={getCitationKey(citation, index)}
                            onClick={() => onCitationClick?.(citation)}
                            className="flex items-center gap-3 p-3 bg-white/50 dark:bg-slate-800/50 rounded-xl border border-outline-variant/10 dark:border-slate-700/50 hover:border-primary/30 dark:hover:border-primary/30 hover:bg-primary/5 dark:hover:bg-primary/5 cursor-pointer transition-all group"
                        >
                            {citation.type === 'asset' ? (
                                <AuthenticatedAssetImage citation={citation} className="h-12 w-12 shrink-0 rounded-lg border border-slate-200 dark:border-slate-700" />
                            ) : (
                                ICON_MAP[citation.type || 'document'] || ICON_MAP.document
                            )}
                            <div className="overflow-hidden flex-1 text-left">
                                <p className="text-xs font-bold text-on-surface dark:text-slate-100 truncate group-hover:text-primary transition-colors">
                                    {citation.type === 'asset' ? getAssetCaption(citation) : citation.title}
                                </p>
                                <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">
                                    {citation.type === 'asset'
                                        ? getAssetLocation(citation) || getAssetCaption(citation)
                                        : citation.description || citation.page ? `${citation.page || 'Da liet ke'}` : 'Tai lieu dinh kem'}
                                </p>
                            </div>
                            <ExternalLink size={14} className="text-slate-400 dark:text-slate-500 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </button>
                    ))
                )}
            </div>
        </div>
    )
}
