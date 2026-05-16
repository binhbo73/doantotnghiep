'use client'

import { useState } from 'react'
import Image from 'next/image'
import { Badge } from '@/components/ui/badge'
import { Small } from '@/components/ui/text'

export interface DocumentAsset {
    id: string
    document_id: string
    chunk_id: string | null
    asset_type: string
    page_number: number | null
    sheet_name: string | null
    anchor_cell: string | null
    anchor_row: number | null
    paragraph_index: number | null
    image_url: string | null
    thumbnail_url: string | null
    image_width: number | null
    image_height: number | null
    image_size_bytes: number
    image_format: string
    ocr_text: string | null
    ocr_confidence: number | null
    caption: string | null
    caption_model: string
    context_text: string | null
    processing_status: string
    processed_at: string | null
    created_at: string
}

interface AssetThumbnailProps {
    asset: DocumentAsset
    className?: string
    onViewDocument?: (documentId: string) => void
}

/**
 * AssetThumbnail - Hiển thị thumbnail ảnh trích xuất từ tài liệu.
 *
 * Dùng trong chat citation: khi AI trả về asset_id, hiển thị ảnh kèm caption.
 *
 * @example
 * <AssetThumbnail asset={asset} />
 */
export function AssetThumbnail({ asset, className = '', onViewDocument }: AssetThumbnailProps) {
    const [expanded, setExpanded] = useState(false)
    const [imgError, setImgError] = useState(false)

    const thumbnailSrc = `/api/v1/assets/${asset.id}/thumbnail`
    const fullSrc = asset.image_url || thumbnailSrc

    // Format location string
    const locationParts: string[] = []
    if (asset.sheet_name) locationParts.push(`Sheet ${asset.sheet_name}`)
    if (asset.anchor_cell) locationParts.push(`Cell ${asset.anchor_cell}`)
    if (asset.page_number) locationParts.push(`Page ${asset.page_number}`)
    if (asset.paragraph_index != null) locationParts.push(`Para ${asset.paragraph_index + 1}`)
    const locationStr = locationParts.join(', ')

    // Format caption model badge
    const modelLabel =
        asset.caption_model === 'qwen25-vl-3b'
            ? 'VL'
            : asset.caption_model === 'rule-based'
              ? 'OCR'
              : asset.caption_model

    if (imgError) return null

    return (
        <div className={`inline-flex flex-col gap-1 ${className}`}>
            {/* Thumbnail */}
            <div
                className={`
          relative cursor-pointer border border-border rounded-lg overflow-hidden
          bg-muted transition-all duration-200 hover:shadow-md
          ${expanded ? 'w-full max-w-md' : 'w-28 h-28'}
          group
        `}
                onClick={() => setExpanded(!expanded)}
                title={asset.caption || 'Click to expand'}
            >
                <Image
                    src={expanded ? fullSrc! : thumbnailSrc!}
                    alt={asset.caption || 'Document asset'}
                    width={expanded ? 400 : 112}
                    height={expanded ? 400 : 112}
                    className="object-cover w-full h-full"
                    onError={() => setImgError(true)}
                    unoptimized
                />

                {/* Expand hint */}
                {!expanded && (
                    <div className="absolute bottom-1 right-1 bg-black/60 text-white text-[10px] px-1 py-0.5 rounded leading-none">
                        ⊕
                    </div>
                )}

                {/* Model badge */}
                <div className="absolute top-1 left-1">
                    <Badge variant="neutral" size="sm" shape="rounded" className="text-[9px] px-1 py-0 leading-none bg-black/50 text-white border-0">
                        {modelLabel}
                    </Badge>
                </div>
            </div>

            {/* Location + Caption preview */}
            <div className="max-w-[112px]">
                {locationStr && (
                    <Small className="text-muted-foreground truncate block font-medium">
                        {locationStr}
                    </Small>
                )}
                {asset.caption && !expanded && (
                    <Small className="text-muted-foreground truncate block">
                        {asset.caption.slice(0, 60)}
                    </Small>
                )}
            </div>

            {/* Expanded detail */}
            {expanded && (
                <div className="mt-2 bg-card border border-border rounded-lg p-3 max-w-md">
                    {/* Caption */}
                    {asset.caption && (
                        <div className="mb-2">
                            <Small className="text-muted-foreground font-medium">Mô tả:</Small>
                            <p className="text-sm text-foreground mt-0.5">{asset.caption}</p>
                        </div>
                    )}

                    {/* OCR text */}
                    {asset.ocr_text && (
                        <div className="mb-2">
                            <Small className="text-muted-foreground font-medium">OCR:</Small>
                            <p className="text-xs text-muted-foreground mt-0.5 font-mono">
                                {asset.ocr_text.slice(0, 300)}
                            </p>
                        </div>
                    )}

                    {/* Context */}
                    {asset.context_text && (
                        <div className="mb-2">
                            <Small className="text-muted-foreground font-medium">Ngữ cảnh:</Small>
                            <p className="text-xs text-muted-foreground mt-0.5">
                                {asset.context_text.slice(0, 200)}
                            </p>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-2 mt-3 pt-2 border-t border-border">
                        {onViewDocument && (
                            <button
                                onClick={() => onViewDocument(asset.document_id)}
                                className="text-xs text-primary hover:underline"
                            >
                                📄 Xem tài liệu
                            </button>
                        )}
                        <button
                            onClick={() => setExpanded(false)}
                            className="text-xs text-muted-foreground hover:underline ml-auto"
                        >
                            Thu gọn
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}

export default AssetThumbnail
