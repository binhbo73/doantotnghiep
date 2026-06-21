'use client'

import { AppIcon } from '@/components/ui/AppIcon'
import { DeleteConfirmDialog } from '@/components/common/DeleteConfirmDialog'
import { FolderDocumentResponse } from '@/services/folder'
import { useRBAC } from '@/hooks/useRBAC'
import { ScopeBadge } from './FolderTreeNode'
import { PreviewModal } from './PreviewModal'
import { UpdateDocumentVersionModal } from './UpdateDocumentVersionModal'
import { api } from '@/services/api/client'
import { ApiError } from '@/services/api/errors'
import { deleteDocument } from '@/services/document'
import React, { useState } from 'react'
import { toast } from 'sonner'

interface DocumentRowProps {
    document: FolderDocumentResponse
    isSelected: boolean
    onSelect: () => void
    folderName?: string
    departmentName?: string
    depth?: number
    onDocumentDeleted?: (documentId: string) => void | Promise<void>
    onVersionCreated?: () => void
}

function getFileIcon(fileType: string): { icon: string; color: string; bg: string } {
    const type = fileType?.toLowerCase() || ''
    if (type.includes('pdf')) return { icon: 'picture_as_pdf', color: 'text-red-600', bg: 'bg-red-50' }
    if (type.includes('doc') || type.includes('word')) return { icon: 'article', color: 'text-blue-600', bg: 'bg-blue-50' }
    if (type.includes('xls') || type.includes('excel') || type.includes('sheet')) return { icon: 'table_chart', color: 'text-green-600', bg: 'bg-green-50' }
    if (type.includes('ppt') || type.includes('powerpoint') || type.includes('presentation')) return { icon: 'slideshow', color: 'text-orange-600', bg: 'bg-orange-50' }
    if (type.includes('zip') || type.includes('rar') || type.includes('tar') || type.includes('gz')) return { icon: 'folder_zip', color: 'text-amber-600', bg: 'bg-amber-50' }
    if (type.includes('png') || type.includes('jpg') || type.includes('jpeg') || type.includes('gif') || type.includes('svg') || type.includes('webp')) return { icon: 'image', color: 'text-purple-600', bg: 'bg-purple-50' }
    if (type.includes('mp4') || type.includes('avi') || type.includes('mov') || type.includes('video')) return { icon: 'movie', color: 'text-pink-600', bg: 'bg-pink-50' }
    if (type.includes('txt') || type.includes('text')) return { icon: 'text_snippet', color: 'text-slate-600', bg: 'bg-slate-100' }
    if (type.includes('md') || type.includes('markdown')) return { icon: 'code', color: 'text-indigo-600', bg: 'bg-indigo-50' }
    if (type.includes('json') || type.includes('xml') || type.includes('yaml') || type.includes('yml')) return { icon: 'data_object', color: 'text-teal-600', bg: 'bg-teal-50' }
    return { icon: 'draft', color: 'text-slate-500', bg: 'bg-slate-100' }
}

function formatFileSize(bytes: number): string {
    const safeBytes = Number(bytes)
    if (!Number.isFinite(safeBytes) || safeBytes <= 0) return '0 B'

    const units = ['B', 'KB', 'MB', 'GB']
    const unitIndex = Math.min(Math.floor(Math.log(safeBytes) / Math.log(1024)), units.length - 1)
    const size = (safeBytes / Math.pow(1024, unitIndex)).toFixed(unitIndex > 0 ? 1 : 0)
    return `${size} ${units[unitIndex]}`
}

export function DocumentRow({
    document,
    isSelected,
    onSelect,
    folderName,
    departmentName,
    onDocumentDeleted,
    onVersionCreated,
}: DocumentRowProps) {
    const { canWrite, canDelete, canRead, hasAnyPermission, hasPermission } = useRBAC()
    const [isPreviewOpen, setIsPreviewOpen] = useState(false)
    const [previewUrl, setPreviewUrl] = useState('')
    const [previewFileType, setPreviewFileType] = useState('')
    const [isVersionModalOpen, setIsVersionModalOpen] = useState(false)
    const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
    const [isBusy, setIsBusy] = useState(false)
    const [isDeleting, setIsDeleting] = useState(false)

    const perm = document.my_permission
    const canInspectUploader = hasAnyPermission(['document_share', 'document_update', 'document_delete'])
    const canOpenDocument = hasPermission('document_read') || canRead(perm)
    const canUpdateVersion = canWrite(perm) && document.is_current !== false
    const canDeleteCurrentDocument = canDelete(perm)

    const fileIcon = getFileIcon(document.file_type)
    const displayName = document.original_name || document.filename || 'Tài liệu'
    const isRestricted = !canOpenDocument

    const stopRowAction = (event: React.MouseEvent<HTMLButtonElement>) => {
        event.stopPropagation()
    }

    const handlePreview = async (event: React.MouseEvent<HTMLButtonElement>) => {
        stopRowAction(event)
        if (!canOpenDocument || isBusy) return

        setIsBusy(true)
        const toastId = toast.loading('Đang chuẩn bị xem trước...')

        try {
            const blob = await api.download(`/documents/${document.id}/preview`)
            if (!blob || blob.size === 0) {
                throw new Error('File rỗng hoặc không hợp lệ')
            }

            const blobType = blob.type?.toLowerCase() || ''
            if (blobType.includes('application/json') || blobType.includes('text/html')) {
                throw new Error('Phản hồi xem trước không hợp lệ')
            }

            const url = URL.createObjectURL(blob)
            setPreviewUrl(url)
            setPreviewFileType(blob.type || document.file_type)
            setIsPreviewOpen(true)
            toast.success('Đã mở bản xem trước', { id: toastId })
        } catch (error) {
            console.error('Document row preview failed:', error)

            if (error instanceof ApiError && error.statusCode === 403) {
                toast.error('Bạn không có quyền xem tài liệu này', { id: toastId })
            } else {
                toast.error('Không thể xem trước tài liệu', { id: toastId })
            }
        } finally {
            setIsBusy(false)
        }
    }

    const handleOpenVersionModal = (event: React.MouseEvent<HTMLButtonElement>) => {
        stopRowAction(event)
        if (!canUpdateVersion) return
        setIsVersionModalOpen(true)
    }

    const handleOpenDeleteDialog = (event: React.MouseEvent<HTMLButtonElement>) => {
        stopRowAction(event)
        if (!canDeleteCurrentDocument) return
        setIsDeleteDialogOpen(true)
    }

    const handleDelete = async () => {
        if (!canDeleteCurrentDocument || isDeleting) return

        setIsDeleting(true)
        try {
            await deleteDocument(document.id)
            setIsDeleteDialogOpen(false)
            toast.success(`Đã xóa tài liệu "${displayName}"`)
            await onDocumentDeleted?.(document.id)
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Không thể xóa tài liệu'
            toast.error(message)
        } finally {
            setIsDeleting(false)
        }
    }

    return (
        <>
            <div
                onClick={!isRestricted ? onSelect : undefined}
                className={`group flex items-center gap-3 px-3 py-2 rounded-lg ${isRestricted ? 'cursor-not-allowed opacity-70' : 'cursor-pointer'} transition-all duration-200 select-none ${isSelected
                    ? 'bg-[#fff3e0] ring-1 ring-[#9d4300]/30 shadow-sm'
                    : isRestricted ? 'hover:bg-red-50/30' : 'hover:bg-white hover:shadow-sm'
                    }`}
            >
                {isRestricted ? (
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-red-50 text-red-500 transition-transform group-hover:scale-105">
                        <AppIcon name="lock" className="text-base" />
                    </div>
                ) : (
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${fileIcon.bg} ${fileIcon.color} transition-transform group-hover:scale-105`}>
                        <AppIcon name={fileIcon.icon} className="text-base" />
                    </div>
                )}

                {isRestricted ? (
                    <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold truncate leading-tight text-red-600">
                            {displayName}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[10px] text-red-500 font-medium">Tài liệu bị giới hạn truy cập</span>
                            {document.department_id && (
                                <>
                                    <span className="text-[10px] text-slate-300">•</span>
                                    <span className="text-[10px] text-slate-500">Phòng ban khác</span>
                                </>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="flex-1 min-w-0">
                        <p className={`text-xs font-semibold truncate leading-tight ${isSelected ? 'text-[#9d4300]' : 'text-slate-800'}`}>
                            {displayName}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                            <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase ${
                                document.is_current
                                    ? 'bg-emerald-100 text-emerald-700'
                                    : 'bg-slate-200 text-slate-600'
                            }`}>
                                v{document.version || 1} · {document.is_current ? 'Hiệu lực' : 'Lịch sử'}
                            </span>
                            <ScopeBadge scope={document.access_scope} />
                            <span className="text-[10px] text-slate-300">•</span>
                            <span className="text-[10px] text-slate-400 uppercase font-medium">{document.file_type}</span>
                            <span className="text-[10px] text-slate-300">•</span>
                            <span className="text-[10px] text-slate-400">{formatFileSize(document.file_size)}</span>
                            {(folderName || departmentName) && (
                                <>
                                    <span className="text-[10px] text-slate-300">•</span>
                                    <div className="flex items-center gap-2">
                                        {folderName && (
                                            <span className="text-[10px] bg-slate-50 px-2 py-0.5 rounded text-slate-500 border border-slate-100">{folderName}</span>
                                        )}
                                        {departmentName && (
                                            <span className="text-[10px] bg-slate-50 px-2 py-0.5 rounded text-slate-500 border border-slate-100">{departmentName}</span>
                                        )}
                                    </div>
                                </>
                            )}
                            {canInspectUploader && document.uploader_name && (
                                <>
                                    <span className="text-[10px] text-slate-300">•</span>
                                    <span className="text-[10px] bg-yellow-50 px-2 py-0.5 rounded text-yellow-700 border border-yellow-100">{document.uploader_name}</span>
                                </>
                            )}
                        </div>
                    </div>
                )}

                {!isRestricted && (
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        {canOpenDocument && (
                            <button
                                type="button"
                                onClick={handlePreview}
                                disabled={isBusy}
                                className="p-1.5 hover:bg-slate-100 rounded text-slate-500 disabled:cursor-wait disabled:opacity-50"
                                title="Xem trước"
                                aria-label={`Xem trước ${displayName}`}
                            >
                                <AppIcon name="visibility" className="text-sm" />
                            </button>
                        )}
                        {canUpdateVersion && (
                            <button
                                type="button"
                                onClick={handleOpenVersionModal}
                                className="p-1.5 hover:bg-slate-100 rounded text-slate-500"
                                title="Cập nhật phiên bản mới"
                                aria-label={`Cập nhật phiên bản mới cho ${displayName}`}
                            >
                                <AppIcon name="update" className="text-sm" />
                            </button>
                        )}
                        {canDeleteCurrentDocument && (
                            <button
                                type="button"
                                onClick={handleOpenDeleteDialog}
                                disabled={isDeleting}
                                className="p-1.5 hover:bg-red-50 rounded text-red-500 disabled:cursor-wait disabled:opacity-50"
                                title="Xóa"
                                aria-label={`Xóa ${displayName}`}
                            >
                                <AppIcon name="delete" className="text-sm" />
                            </button>
                        )}
                    </div>
                )}
            </div>

            <PreviewModal
                isOpen={isPreviewOpen}
                onClose={() => {
                    setIsPreviewOpen(false)
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
            <UpdateDocumentVersionModal
                isOpen={isVersionModalOpen}
                document={document}
                onClose={() => setIsVersionModalOpen(false)}
                onSuccess={() => {
                    setIsVersionModalOpen(false)
                    onVersionCreated?.()
                }}
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
        </>
    )
}

export { getFileIcon, formatFileSize }
