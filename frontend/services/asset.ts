/**
 * Asset API Service - Gọi API cho Document Assets (OCR + VL Caption)
 *
 * Endpoints:
 * - GET /api/v1/documents/{doc_id}/assets  - List assets
 * - GET /api/v1/assets/{asset_id}          - Asset detail
 * - GET /api/v1/assets/{asset_id}/thumbnail - Thumbnail image
 */

import { apiClient } from '@/lib/api-client'

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

/**
 * Lấy danh sách assets của một document.
 */
export async function getDocumentAssets(documentId: string): Promise<DocumentAsset[]> {
    const response = await apiClient.get(`/documents/${documentId}/assets`)
    return response.data?.data || []
}

/**
 * Lấy chi tiết một asset.
 */
export async function getAssetDetail(assetId: string): Promise<DocumentAsset> {
    const response = await apiClient.get(`/assets/${assetId}`)
    return response.data?.data
}

/**
 * Lấy URL thumbnail cho asset.
 */
export function getAssetThumbnailUrl(assetId: string): string {
    return `/api/v1/assets/${assetId}/thumbnail`
}
