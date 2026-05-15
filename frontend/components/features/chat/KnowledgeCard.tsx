'use client'

import React from 'react'
import { FileText, File, ExternalLink, Zap } from 'lucide-react'

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
    document_id?: string
    chunk_id?: string
    source?: string
    score?: number
    url?: string
    type?: string
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
}

const getCitationKey = (citation: Citation, index: number) => {
    return [
        citation.document_id || 'doc',
        citation.chunk_id || 'chunk',
        citation.id || citation.number || 'source',
        index,
    ].join('-')
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
            citation.chunk_id || citation.excerpt || citation.description || '',
        ].join('|')

        return list.findIndex((item) => {
            const itemKey = [
                item.document_id || item.title,
                item.page || '',
                item.chunk_id || item.excerpt || item.description || '',
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
                            {ICON_MAP[citation.type || 'document'] || ICON_MAP.document}
                            <div className="overflow-hidden flex-1 text-left">
                                <p className="text-xs font-bold text-on-surface dark:text-slate-100 truncate group-hover:text-primary transition-colors">
                                    {citation.title}
                                </p>
                                <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">
                                    {citation.description || citation.page ? `${citation.page || 'Đã liệt kê'}` : 'Tài liệu đính kèm'}
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
