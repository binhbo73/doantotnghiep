'use client'

import { AppIcon } from '@/components/ui/AppIcon'
import React, { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { FolderDocumentResponse } from '@/services/folder'
import { uploadDocumentVersion } from '@/services/upload'

interface UpdateDocumentVersionModalProps {
    isOpen: boolean
    document: FolderDocumentResponse
    onClose: () => void
    onSuccess?: () => void
}

export function UpdateDocumentVersionModal({
    isOpen,
    document,
    onClose,
    onSuccess,
}: UpdateDocumentVersionModalProps) {
    const [file, setFile] = useState<File | null>(null)
    const [changeSummary, setChangeSummary] = useState('')
    const [progress, setProgress] = useState(0)
    const [isUploading, setIsUploading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        if (!isOpen) return
        setFile(null)
        setChangeSummary('')
        setProgress(0)
        setIsUploading(false)
        setError(null)
    }, [isOpen, document.id])

    if (!isOpen) return null

    const submit = async () => {
        if (!file) {
            setError('Vui lòng chọn file cho phiên bản mới.')
            return
        }
        setIsUploading(true)
        setError(null)
        try {
            await uploadDocumentVersion(document.id, file, {
                versionLock: document.version_lock,
                changeSummary,
                updateMode: 'auto',
                onProgress: (value) => setProgress(value.percentage),
            })
            toast.success('Đã tải phiên bản mới. Bản hiện tại vẫn được dùng cho đến khi xử lý hoàn tất.')
            onSuccess?.()
            onClose()
        } catch (uploadError) {
            setError(uploadError instanceof Error ? uploadError.message : 'Không thể tạo phiên bản mới.')
        } finally {
            setIsUploading(false)
        }
    }

    return (
        <div className="fixed inset-0 z-[120] flex items-center justify-center bg-slate-900/55 p-4 backdrop-blur-sm">
            <div className="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
                    <div>
                        <h2 className="text-base font-bold text-slate-900">Cập nhật phiên bản tài liệu</h2>
                        <p className="mt-1 text-xs text-slate-500">Phiên bản hiện tại: v{document.version || 1}</p>
                    </div>
                    <button type="button" onClick={onClose} disabled={isUploading} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100">
                        <AppIcon name="close" className="text-lg" />
                    </button>
                </div>
                <div className="space-y-5 p-6">
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-relaxed text-amber-800">
                        Hệ thống tạo một bản staging độc lập. Phiên bản cũ chỉ bị thay thế sau khi parse,
                        chunk và embedding của bản mới hoàn tất.
                    </div>
                    <div className="rounded-xl border border-blue-100 bg-blue-50 p-3 text-xs leading-relaxed text-blue-800">
                        Hệ thống tự so sánh với phiên bản hiện tại để xác định file là bản sửa đổi
                        một phần hay bản đầy đủ thay thế. Các phần cũ không bị sửa đổi vẫn được kế thừa.
                    </div>
                    {error && <div className="rounded-xl border border-red-100 bg-red-50 p-3 text-sm text-red-600">{error}</div>}
                    <div>
                        <label className="mb-2 block text-sm font-semibold text-slate-700">File phiên bản mới</label>
                        <input
                            type="file"
                            accept=".pdf,.doc,.docx,.pptx,.txt,.md,.xlsx,.xls,.csv"
                            disabled={isUploading}
                            onChange={(event) => setFile(event.target.files?.[0] || null)}
                            className="block w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm"
                        />
                    </div>
                    <div>
                        <label className="mb-2 block text-sm font-semibold text-slate-700">Nội dung thay đổi</label>
                        <textarea
                            rows={4}
                            value={changeSummary}
                            disabled={isUploading}
                            onChange={(event) => setChangeSummary(event.target.value)}
                            placeholder="Ví dụ: Cập nhật Điều 1 và bổ sung Khoản 3..."
                            className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-[#9d4300]"
                        />
                    </div>
                    {isUploading && (
                        <div className="space-y-2">
                            <div className="flex justify-between text-xs font-semibold text-slate-600"><span>Đang tải file</span><span>{progress}%</span></div>
                            <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                                <div className="h-full bg-[#9d4300]" style={{ width: `${progress}%` }} />
                            </div>
                        </div>
                    )}
                </div>
                <div className="flex justify-end gap-3 border-t border-slate-100 bg-slate-50 px-6 py-4">
                    <button type="button" onClick={onClose} disabled={isUploading} className="rounded-xl px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-slate-200">Hủy</button>
                    <button type="button" onClick={submit} disabled={!file || isUploading} className="rounded-xl bg-[#9d4300] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50">
                        {isUploading ? 'Đang tải...' : `Tạo phiên bản v${(document.version || 1) + 1}`}
                    </button>
                </div>
            </div>
        </div>
    )
}
