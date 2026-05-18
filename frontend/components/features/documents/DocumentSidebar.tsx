'use client'

import React, { useState } from 'react'
import { FolderDocumentResponse, FolderResponse } from '@/services/folder'
import { getFileIcon, formatFileSize } from './DocumentRow'
import EffectivePermissionBadge from '@/components/common/EffectivePermissionBadge'
import { PreviewModal } from './PreviewModal'
import { api } from '@/services/api/client'
import { ApiError } from '@/services/api/errors'
import { toast } from 'sonner'
import { useRBAC } from '@/hooks/useRBAC'

interface DocumentSidebarProps {
    document: FolderDocumentResponse | null
    folder: FolderResponse | null
    onClose: () => void
}

function formatDate(dateStr: string): string {
    try {
        const d = new Date(dateStr)
        return d.toLocaleDateString('vi-VN', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
        })
    } catch {
        return dateStr
    }
}

export function DocumentSidebar({ document, folder, onClose }: DocumentSidebarProps) {
    const [isDownloading, setIsDownloading] = useState(false)
    const [isPreviewOpen, setIsPreviewOpen] = useState(false)
    const [previewUrl, setPreviewUrl] = useState<string>('')
    const [previewFileType, setPreviewFileType] = useState<string>('')
    const { canRead, canWrite, canDelete } = useRBAC()

    if (!document) {
        return (
            <div className="col-span-12 lg:col-span-5 bg-white shadow-sm ring-1 ring-slate-100 rounded-2xl p-6 flex flex-col items-center justify-center min-h-[400px]">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center mb-4">
                    <span className="material-symbols-outlined text-4xl text-slate-300">draft</span>
                </div>
                <p className="text-sm font-medium text-slate-500 mb-1">Chọn tài liệu</p>
                <p className="text-xs text-slate-400 text-center max-w-[200px]">
                    Nhấn vào tài liệu trong cây thư mục để xem chi tiết
                </p>
            </div>
        )
    }

    const fileIcon = getFileIcon(document.file_type)
    const displayName = document.original_name || document.filename || 'Tài liệu'
    const canReadDocument = canRead(document.my_permission)
    const canWriteDocument = canWrite(document.my_permission)
    const canDeleteDocument = canDelete(document.my_permission)

    if (!canReadDocument) {
        return (
            <div className="col-span-12 lg:col-span-5 bg-white shadow-sm ring-1 ring-slate-100 rounded-2xl p-6 flex flex-col items-center justify-center min-h-[400px]">
                <div className="w-20 h-20 rounded-2xl bg-red-50 flex items-center justify-center mb-4">
                    <span className="material-symbols-outlined text-4xl text-red-400">lock</span>
                </div>
                <p className="text-sm font-medium text-slate-700 mb-1">Không có quyền xem tài liệu</p>
                <p className="text-xs text-slate-400 text-center max-w-[220px]">
                    Tài liệu này không nằm trong phạm vi truy cập của bạn
                </p>
            </div>
        )
    }

    const handleDownload = async (mode: 'download' | 'preview') => {
        if (!document) return

        setIsDownloading(true)
        const toastId = toast.loading(mode === 'download' ? 'Đang chuẩn bị tải xuống...' : 'Đang chuẩn bị xem trước...')

        try {
            const filename = document.original_name || document.filename || 'document'
            const endpoint = mode === 'preview'
                ? `/documents/${document.id}/preview`
                : `/documents/${document.id}/download`

            if (mode === 'download') {
                // Download: save to disk
                await api.download(endpoint, filename)
                toast.success('Đã tải xuống thành công', { id: toastId })
            } else {
                // Preview uses the original stored file, not converted HTML/table output.
                const blob = await api.download(endpoint)
                if (!blob || blob.size === 0) {
                    throw new Error('File rỗng hoặc không hợp lệ')
                }

                // Avoid opening the preview modal for non-file responses.
                const blobType = blob.type?.toLowerCase() || ''
                const looksLikeErrorResponse = blobType.includes('application/json') || blobType.includes('text/html')
                if (looksLikeErrorResponse) {
                    throw new Error('Phản hồi tải xuống không hợp lệ')
                }

                const url = URL.createObjectURL(blob)
                setPreviewUrl(url)
                setPreviewFileType(blob.type || document.file_type)
                setIsPreviewOpen(true)
                toast.success('Đã mở bản xem trước', { id: toastId })
            }
        } catch (error) {
            console.error('Download/Preview failed:', error)

            if (error instanceof ApiError && error.statusCode === 403) {
                toast.error('Bạn không có quyền xem tài liệu này', { id: toastId })
                return
            }

            toast.error(mode === 'download' ? 'Tải xuống thất bại' : 'Không thể xem trước tài liệu', { id: toastId })
        } finally {
            setIsDownloading(false)
        }
    }

    return (
        <div className="col-span-12 lg:col-span-5 bg-white shadow-sm ring-1 ring-slate-100 rounded-2xl overflow-hidden flex flex-col max-h-[85vh]">
            {/* Preview Header */}
            <div className="relative h-44 bg-gradient-to-br from-[#f97316]/10 via-[#fff7ed] to-[#fef3c7] flex items-center justify-center flex-shrink-0">
                {/* Close button */}
                <button
                    onClick={onClose}
                    className="absolute top-3 right-3 w-7 h-7 rounded-lg bg-white/80 backdrop-blur-sm flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-white transition-all shadow-sm"
                >
                    <span className="material-symbols-outlined text-base">close</span>
                </button>

                {/* Large file icon */}
                <div className={`w-20 h-20 rounded-2xl flex items-center justify-center ${fileIcon.bg} ${fileIcon.color} shadow-lg`}>
                    <span className="material-symbols-outlined text-4xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                        {fileIcon.icon}
                    </span>
                </div>
            </div>

            {/* Content */}
            <div className="p-5 space-y-5 overflow-y-auto flex-1">
                {/* File Name & Type */}
                <div>
                    <div className="flex items-center gap-2">
                        <h3 className="text-sm font-bold text-slate-900 leading-snug mb-1">{displayName}</h3>
                        <EffectivePermissionBadge resource={document} resourceType="document" />
                    </div>
                    <p className="text-[11px] text-slate-400">
                        Tệp tin {document.file_type?.toUpperCase()} • {formatFileSize(document.file_size)}
                    </p>
                </div>

                {/* Detail Info Grid */}
                <div className="space-y-3">
                    <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Chi tiết tài liệu</h4>

                    <div className="grid grid-cols-2 gap-3">
                        {/* File Type */}
                        <div className="space-y-1">
                            <span className="text-[10px] font-medium text-slate-400">Định dạng</span>
                            <p className="text-xs font-semibold text-slate-700 uppercase">{document.file_type}</p>
                        </div>

                        {/* Created Date */}
                        <div className="space-y-1">
                            <span className="text-[10px] font-medium text-slate-400">Ngày tạo</span>
                            <p className="text-xs font-semibold text-slate-700">{formatDate(document.created_at)}</p>
                        </div>

                        {/* Updated Date */}
                        <div className="space-y-1">
                            <span className="text-[10px] font-medium text-slate-400">Lần cuối sửa</span>
                            <p className="text-xs font-semibold text-slate-700">{formatDate(document.updated_at)}</p>
                        </div>
                    </div>
                </div>

                {/* Folder Location */}
                {folder && (
                    <div className="space-y-2">
                        <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Phạm vi truy cập</h4>
                        <div className="flex items-center gap-2 px-3 py-2.5 bg-[#fef5ed] rounded-xl border border-[#f97316]/10">
                            <span className="material-symbols-outlined text-[#9d4300] text-base" style={{ fontVariationSettings: "'FILL' 1" }}>
                                folder
                            </span>
                            <div className="min-w-0">
                                <p className="text-xs font-semibold text-[#9d4300] truncate">{folder.name}</p>
                                <p className="text-[10px] text-[#9d4300]/60 capitalize">{folder.access_scope}</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* AI Processing Section */}
                <div className="space-y-2">
                    <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">AI Processing</h4>
                    <div className="p-3 bg-gradient-to-r from-violet-50 to-indigo-50 rounded-xl border border-violet-100">
                        <p className="text-[11px] text-violet-700 leading-relaxed">
                            Tài liệu đang sẵn sàng cho các tác vụ tìm kiếm và khai thác tri thức trong hệ thống.
                        </p>
                    </div>
                </div>

                {/* Primary Actions */}
                <div className="space-y-3 pt-2">
                    <div className="flex gap-2">
                        <button
                            onClick={() => handleDownload('download')}
                            disabled={isDownloading}
                            className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 bg-[#9d4300] text-white rounded-xl text-xs font-bold hover:bg-[#b75b00] transition-colors shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Tải file gốc về máy"
                        >
                            <span className="material-symbols-outlined text-sm">download</span>
                            Tải xuống
                        </button>

                        <button
                            onClick={() => handleDownload('preview')}
                            disabled={isDownloading}
                            className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 bg-slate-800 text-white rounded-xl text-xs font-bold hover:bg-slate-900 transition-colors shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Xem nội dung tài liệu trực tiếp"
                        >
                            <span className="material-symbols-outlined text-sm">visibility</span>
                            Xem trước
                        </button>
                    </div>

                    {/* Secondary Actions */}
                    {(canWriteDocument || canDeleteDocument) && (
                        <div className="flex gap-2 pt-1">
                            {canWriteDocument && (
                                <button
                                    className="flex-[2] flex items-center justify-center gap-1.5 px-4 py-2.5 border border-slate-200 text-slate-700 bg-white rounded-xl text-xs font-bold hover:bg-slate-50 hover:border-slate-300 transition-all"
                                    title="Sửa file ở máy tính sau đó tải lên bản mới"
                                >
                                    <span className="material-symbols-outlined text-sm text-[#9d4300]">update</span>
                                    Cập nhật phiên bản mới
                                </button>
                            )}

                            {canDeleteDocument && (
                                <button
                                    className="px-3 py-2.5 border border-red-100 text-red-500 bg-red-50 rounded-xl text-xs font-bold hover:bg-red-100 transition-colors"
                                    title="Xóa tài liệu này"
                                >
                                    <span className="material-symbols-outlined text-sm">delete</span>
                                </button>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Preview Modal */}
            <PreviewModal
                isOpen={isPreviewOpen}
                onClose={() => {
                    setIsPreviewOpen(false)
                    // Clean up object URL
                    if (previewUrl.startsWith('blob:')) {
                        URL.revokeObjectURL(previewUrl)
                    }
                    setPreviewUrl('')
                    setPreviewFileType('')
                }}
                documentId={document.id}
                fileUrl={previewUrl}
                fileName={displayName}
                fileType={previewFileType || document.file_type}
            />
        </div>
    )
}
