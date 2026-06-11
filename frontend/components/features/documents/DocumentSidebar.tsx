'use client'

import { AppIcon } from '@/components/ui/AppIcon'
import React, { useEffect, useState } from 'react'
import { FolderDocumentResponse, FolderResponse } from '@/services/folder'
import { getFileIcon, formatFileSize } from './DocumentRow'
import EffectivePermissionBadge from '@/components/common/EffectivePermissionBadge'
import { PreviewModal } from './PreviewModal'
import { api } from '@/services/api/client'
import { ApiError } from '@/services/api/errors'
import { toast } from 'sonner'
import { useRBAC } from '@/hooks/useRBAC'
import { deleteDocument, getDocumentStatus, getDocumentVersions } from '@/services/document'
import { UpdateDocumentVersionModal } from './UpdateDocumentVersionModal'
import { DeleteConfirmDialog } from '@/components/common/DeleteConfirmDialog'

type SidebarDocumentStatus = {
    document_status?: string
    current_stage_label?: string
    progress_percent?: number
    ready_for_chat?: boolean
    processing_steps?: Array<{
        key: string
        label: string
        status: 'not_started' | 'in_progress' | 'completed' | 'failed' | string
    }>
    metadata?: {
        processing_error?: string
    }
    document_error?: string
}

interface DocumentSidebarProps {
    document: FolderDocumentResponse | null
    folder: FolderResponse | null
    onClose: () => void
    onVersionCreated?: () => void
    onSelectVersion?: (document: FolderDocumentResponse) => void
    onDocumentDeleted?: (documentId: string) => void | Promise<void>
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

export function DocumentSidebar({
    document,
    folder,
    onClose,
    onVersionCreated,
    onSelectVersion,
    onDocumentDeleted,
}: DocumentSidebarProps) {
    const [isDownloading, setIsDownloading] = useState(false)
    const [isPreviewOpen, setIsPreviewOpen] = useState(false)
    const [previewUrl, setPreviewUrl] = useState<string>('')
    const [previewFileType, setPreviewFileType] = useState<string>('')
    const [documentStatus, setDocumentStatus] = useState<SidebarDocumentStatus | null>(null)
    const [statusLoading, setStatusLoading] = useState(false)
    const [statusError, setStatusError] = useState<string | null>(null)
    const [isVersionModalOpen, setIsVersionModalOpen] = useState(false)
    const [versions, setVersions] = useState<FolderDocumentResponse[]>([])
    const [versionRefreshKey, setVersionRefreshKey] = useState(0)
    const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
    const [isDeleting, setIsDeleting] = useState(false)
    const { canRead, canWrite, canDelete, hasPermission } = useRBAC()
    const effectivePermission = document?.my_permission ?? 'none'
    const canReadDocumentForStatus = !!document && canRead(effectivePermission)
    const selectedDocumentId = document?.id

    useEffect(() => {
        if (!selectedDocumentId || !canReadDocumentForStatus) {
            setDocumentStatus(null)
            setStatusLoading(false)
            setStatusError(null)
            return
        }

        let isActive = true

        const loadStatus = async () => {
            setStatusLoading(true)
            setStatusError(null)

            try {
                const response = await getDocumentStatus(selectedDocumentId)
                const payload = response.data || response

                if (!isActive) return

                setDocumentStatus(payload)
            } catch (error) {
                if (!isActive) return

                console.error('Failed to load document status:', error)
                setDocumentStatus(null)
                setStatusError('Không thể tải trạng thái xử lý')
            } finally {
                if (isActive) {
                    setStatusLoading(false)
                }
            }
        }

        void loadStatus()

        return () => {
            isActive = false
        }
    }, [selectedDocumentId, canReadDocumentForStatus])

    useEffect(() => {
        if (!selectedDocumentId || !canReadDocumentForStatus) {
            setVersions([])
            return
        }
        let active = true
        void getDocumentVersions(selectedDocumentId)
            .then((items) => {
                if (active) setVersions(items)
            })
            .catch(() => {
                if (active) setVersions([])
            })
        return () => {
            active = false
        }
    }, [selectedDocumentId, canReadDocumentForStatus, versionRefreshKey])

    if (!document) {
        return (
            <div className="col-span-12 lg:col-span-5 bg-white shadow-sm ring-1 ring-slate-100 rounded-2xl p-6 flex flex-col items-center justify-center min-h-[400px]">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center mb-4">
                    <AppIcon name="draft" className="text-4xl text-slate-300" />
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
    const canReadDocument = canReadDocumentForStatus
    const canWriteDocument = canWrite(effectivePermission)
    const canDeleteDocument = canDelete(effectivePermission)
    const canDownloadDocument = hasPermission('document_download') && canReadDocument
    const statusLabel = documentStatus?.current_stage_label || 'Tài liệu đã sẵn sàng'
    const statusProgress = typeof documentStatus?.progress_percent === 'number'
        ? documentStatus.progress_percent
        : document.status === 'completed'
            ? 100
            : document.status === 'processing'
                ? 65
                : 0
    const isReadyForChat = documentStatus?.ready_for_chat === true || document.status === 'completed'
    const statusMessage = documentStatus?.document_status === 'failed'
        ? documentStatus.metadata?.processing_error || documentStatus.document_error || 'Xử lý tài liệu thất bại'
        : isReadyForChat
            ? 'Tài liệu sẵn sàng cho tìm kiếm và chat.'
            : 'Trạng thái được tải khi bạn chọn tài liệu trong sidebar.'

    const handleDelete = async () => {
        if (!canDeleteDocument || isDeleting) return

        setIsDeleting(true)
        try {
            await deleteDocument(document.id)
            setIsDeleteDialogOpen(false)
            toast.success(`Đã xóa tài liệu "${displayName}"`)
            await onDocumentDeleted?.(document.id)
            onClose()
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Không thể xóa tài liệu'
            toast.error(message)
        } finally {
            setIsDeleting(false)
        }
    }

    if (!canReadDocument) {
        return (
            <div className="col-span-12 lg:col-span-5 bg-white shadow-sm ring-1 ring-slate-100 rounded-2xl p-6 flex flex-col items-center justify-center min-h-[400px]">
                <div className="w-20 h-20 rounded-2xl bg-red-50 flex items-center justify-center mb-4">
                    <AppIcon name="lock" className="text-4xl text-red-400" />
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
        if (mode === 'download' && !canDownloadDocument) return

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
                    <AppIcon name="close" className="text-base" />
                </button>

                {/* Large file icon */}
                <div className={`w-20 h-20 rounded-2xl flex items-center justify-center ${fileIcon.bg} ${fileIcon.color} shadow-lg`}>
                    <AppIcon name={fileIcon.icon} className="text-4xl" />
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
                        Tệp tin {document.file_type?.toUpperCase()} • {formatFileSize(document.file_size)} • v{document.version || 1}
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

                        <div className="space-y-1">
                            <span className="text-[10px] font-medium text-slate-400">Trạng thái phiên bản</span>
                            <p className="text-xs font-semibold text-slate-700">
                                v{document.version || 1} · {document.is_current ? 'Đang hiệu lực' : 'Lịch sử'}
                            </p>
                        </div>

                        <div className="space-y-1">
                            <span className="text-[10px] font-medium text-slate-400">Khoảng hiệu lực</span>
                            <p className="text-xs font-semibold text-slate-700">
                                {document.valid_from ? formatDate(document.valid_from) : 'Không xác định'}
                                {' → '}
                                {document.valid_to ? formatDate(document.valid_to) : 'Hiện tại'}
                            </p>
                        </div>
                    </div>
                </div>

                {versions.length > 0 && (
                    <div className="space-y-2">
                        <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                            Lịch sử phiên bản
                        </h4>
                        <div className="space-y-2">
                            {versions.slice(0, 10).map((versionItem) => (
                                <button
                                    key={versionItem.id}
                                    type="button"
                                    onClick={() => onSelectVersion?.(versionItem)}
                                    className={`flex w-full items-center justify-between rounded-xl border px-3 py-2 text-left transition-colors ${
                                        versionItem.id === document.id
                                            ? 'border-[#9d4300]/30 bg-[#fff3e0]'
                                            : 'border-slate-100 bg-slate-50 hover:bg-slate-100'
                                    }`}
                                >
                                    <div className="min-w-0">
                                        <p className="text-xs font-bold text-slate-700">
                                            v{versionItem.version || 1}
                                            {versionItem.is_current ? ' • Đang hiệu lực' : ''}
                                        </p>
                                        <p className="truncate text-[10px] text-slate-400">
                                            {versionItem.change_summary || formatDate(versionItem.created_at)}
                                        </p>
                                    </div>
                                    <span className={`rounded-full px-2 py-1 text-[9px] font-bold uppercase ${
                                        versionItem.version_state === 'active'
                                            ? 'bg-emerald-100 text-emerald-700'
                                            : versionItem.version_state === 'staging'
                                                ? 'bg-amber-100 text-amber-700'
                                                : versionItem.version_state === 'failed'
                                                    ? 'bg-red-100 text-red-700'
                                                    : 'bg-slate-200 text-slate-600'
                                    }`}>
                                        {versionItem.version_state || versionItem.status}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Folder Location */}
                {folder && (
                    <div className="space-y-2">
                        <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Phạm vi truy cập</h4>
                        <div className="flex items-center gap-2 px-3 py-2.5 bg-[#fef5ed] rounded-xl border border-[#f97316]/10">
                            <AppIcon name="folder" className="text-[#9d4300] text-base" />
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
                    <div className="p-3 bg-gradient-to-r from-violet-50 to-indigo-50 rounded-xl border border-violet-100 space-y-3">
                        <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                                <p className="text-[11px] font-semibold text-violet-800 truncate">
                                    {statusLoading ? 'Đang tải trạng thái...' : statusLabel}
                                </p>
                                <p className="text-[11px] text-violet-700 leading-relaxed mt-1">
                                    {statusError || statusMessage}
                                </p>
                            </div>
                            <span className="text-[11px] font-bold text-violet-700">{statusProgress}%</span>
                        </div>

                        <div className="h-2 rounded-full bg-violet-100 overflow-hidden">
                            <div
                                className={`h-full transition-all duration-300 ${isReadyForChat ? 'bg-emerald-500' : 'bg-[#9d4300]'}`}
                                style={{ width: `${statusLoading ? 15 : statusProgress}%` }}
                            />
                        </div>

                        {Array.isArray(documentStatus?.processing_steps) && documentStatus.processing_steps.length > 0 && (
                            <div className="grid grid-cols-1 gap-1.5">
                                {documentStatus.processing_steps.map((step) => (
                                    <div key={step.key} className="flex items-center gap-2 text-[11px] text-violet-700">
                                        <span
                                            className={`h-2 w-2 rounded-full ${step.status === 'completed'
                                                    ? 'bg-emerald-500'
                                                    : step.status === 'in_progress'
                                                        ? 'bg-[#9d4300]'
                                                        : step.status === 'failed'
                                                            ? 'bg-red-500'
                                                            : 'bg-violet-200'
                                                }`}
                                        />
                                        <span className={step.status === 'in_progress' ? 'font-semibold text-violet-900' : ''}>
                                            {step.label}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Primary Actions */}
                <div className="space-y-3 pt-2">
                    <div className="flex gap-2">
                        {canDownloadDocument && (
                            <button
                                onClick={() => handleDownload('download')}
                                disabled={isDownloading}
                                className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 bg-[#9d4300] text-white rounded-xl text-xs font-bold hover:bg-[#b75b00] transition-colors shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                                title="Tải file gốc về máy"
                            >
                                <AppIcon name="download" className="text-sm" />
                                Tải xuống
                            </button>
                        )}

                        <button
                            onClick={() => handleDownload('preview')}
                            disabled={isDownloading}
                            className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 bg-slate-800 text-white rounded-xl text-xs font-bold hover:bg-slate-900 transition-colors shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Xem nội dung tài liệu trực tiếp"
                        >
                            <AppIcon name="visibility" className="text-sm" />
                            Xem trước
                        </button>
                    </div>

                    {/* Secondary Actions */}
                    {(canWriteDocument || canDeleteDocument) && (
                        <div className="flex gap-2 pt-1">
                            {canWriteDocument && document.is_current !== false && (
                                <button
                                    onClick={() => setIsVersionModalOpen(true)}
                                    className="flex-[2] flex items-center justify-center gap-1.5 px-4 py-2.5 border border-slate-200 text-slate-700 bg-white rounded-xl text-xs font-bold hover:bg-slate-50 hover:border-slate-300 transition-all"
                                    title="Sửa file ở máy tính sau đó tải lên bản mới"
                                >
                                    <AppIcon name="update" className="text-sm text-[#9d4300]" />
                                    Cập nhật phiên bản mới
                                </button>
                            )}

                            {canDeleteDocument && (
                                <button
                                    onClick={() => setIsDeleteDialogOpen(true)}
                                    disabled={isDeleting}
                                    className="px-3 py-2.5 border border-red-100 text-red-500 bg-red-50 rounded-xl text-xs font-bold hover:bg-red-100 transition-colors"
                                    title="Xóa tài liệu này"
                                >
                                    <AppIcon name="delete" className="text-sm" />
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
            <DeleteConfirmDialog
                open={isDeleteDialogOpen}
                title="Xóa tài liệu?"
                description="Tài liệu và dữ liệu xử lý liên quan sẽ bị xóa khỏi hệ thống."
                resourceName={displayName}
                isDeleting={isDeleting}
                onOpenChange={setIsDeleteDialogOpen}
                onConfirm={handleDelete}
            />
            <UpdateDocumentVersionModal
                isOpen={isVersionModalOpen}
                document={document}
                onClose={() => setIsVersionModalOpen(false)}
                onSuccess={() => {
                    setVersionRefreshKey((value) => value + 1)
                    onVersionCreated?.()
                }}
            />
        </div>
    )
}
