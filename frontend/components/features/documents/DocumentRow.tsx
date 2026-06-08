'use client'

import { AppIcon } from '@/components/ui/AppIcon'
import { FolderDocumentResponse } from '@/services/folder'
import { useRBAC } from '@/hooks/useRBAC'
import { ScopeBadge } from './FolderTreeNode'

interface DocumentRowProps {
    document: FolderDocumentResponse
    isSelected: boolean
    onSelect: () => void
    folderName?: string
    departmentName?: string
    depth?: number
}

// ─── Helpers ──────────────────────────────────────────────

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
}: DocumentRowProps) {
    const { canWrite, canDelete, canRead, hasAnyPermission, hasPermission } = useRBAC()
    const perm = document.my_permission
    const canInspectUploader = hasAnyPermission(['document_share', 'document_update', 'document_delete'])
    const canOpenDocument = hasPermission('document_read') || canRead(perm)

    const fileIcon = getFileIcon(document.file_type)
    const displayName = document.original_name || document.filename
    const isRestricted = !canOpenDocument

    return (
        <div
            onClick={!isRestricted ? onSelect : undefined}
            className={`group flex items-center gap-3 px-3 py-2 rounded-lg ${isRestricted ? 'cursor-not-allowed opacity-70' : 'cursor-pointer'} transition-all duration-200 select-none ${isSelected
                ? 'bg-[#fff3e0] ring-1 ring-[#9d4300]/30 shadow-sm'
                : isRestricted ? 'hover:bg-red-50/30' : 'hover:bg-white hover:shadow-sm'
                }`}
        >
            {/* File Type Icon or Restricted Lock */}
            {isRestricted ? (
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-red-50 text-red-500 transition-transform group-hover:scale-105">
                    <AppIcon name="lock" className="text-base" />
                </div>
            ) : (
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${fileIcon.bg} ${fileIcon.color} transition-transform group-hover:scale-105`}>
                    <AppIcon name={fileIcon.icon} className="text-base" />
                </div>
            )}

            {/* File Info or Restricted Message */}
            {isRestricted ? (
                <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold truncate leading-tight text-red-600">
                        {displayName}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-red-500 font-medium">🔒 Tài liệu bị giới hạn truy cập</span>
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
                        {/* Folder and Department */}
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
                        {/* Show uploader name only to users with document management permissions */}
                        {canInspectUploader && document.uploader_name && (
                            <>
                                <span className="text-[10px] text-slate-300">•</span>
                                <span className="text-[10px] bg-yellow-50 px-2 py-0.5 rounded text-yellow-700 border border-yellow-100">{document.uploader_name}</span>
                            </>
                        )}
                    </div>
                </div>
            )}

            {/* Action Buttons - Hidden for restricted documents */}
            {!isRestricted && (
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {canOpenDocument && (
                        <button className="p-1.5 hover:bg-slate-100 rounded text-slate-500" title="Xem">
                            <AppIcon name="visibility" className="text-sm" />
                        </button>
                    )}
                    {canWrite(perm) && (
                        <button className="p-1.5 hover:bg-slate-100 rounded text-slate-500" title="Sửa">
                            <AppIcon name="edit" className="text-sm" />
                        </button>
                    )}
                    {canDelete(perm) && (
                        <button className="p-1.5 hover:bg-red-50 rounded text-red-500" title="Xóa">
                            <AppIcon name="delete" className="text-sm" />
                        </button>
                    )}
                </div>
            )}

        </div>
    )
}

// Re-export helpers for use in other components
export { getFileIcon, formatFileSize }
