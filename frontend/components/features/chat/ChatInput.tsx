'use client'

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Paperclip, X, FolderOpen, Search, Check } from 'lucide-react'
import { fetchAvailableAttachments } from '@/services/chatAttachments'
import { FolderDocumentResponse, FolderResponse } from '@/services/folder'
import { ConversationAttachmentPayload } from '@/services/chatService'
import { uploadDocument, getDocumentStatus } from '@/services/document'

export interface ChatUploadAttachment {
    id: string
    name: string
    size: number
    type: string
    progress?: number
    status?: 'uploading' | 'processing' | 'completed' | 'failed'
    statusText?: string
    documentId?: string
}

export interface ChatSelectedResourceItem {
    id: string
    name: string
    detail?: string
}

export interface ChatAttachmentState {
    uploads: ChatUploadAttachment[]
    selectedDocuments: ChatSelectedResourceItem[]
    selectedFolders: ChatSelectedResourceItem[]
    totalSelected: number
    removeUpload?: (id: string) => void
    removeDocument?: (id: string) => void
    removeFolder?: (id: string) => void
    clearAll?: () => void
}

interface ChatInputProps {
    onSendMessage?: (message: string, attachments?: ConversationAttachmentPayload) => void
    onAttachmentStateChange?: (state: ChatAttachmentState) => void
    placeholder?: string
    isLoading?: boolean
    disabled?: boolean
}

export const ChatInput: React.FC<ChatInputProps> = ({
    onSendMessage,
    onAttachmentStateChange,
    placeholder = 'Hỏi tôi bất cứ điều gì về tài liệu và tri thức nội bộ...',
    isLoading = false,
    disabled = false,
}) => {
    const [message, setMessage] = useState('')
    const [attachments, setAttachments] = useState<ChatUploadAttachment[]>([])
    const [showSystemPicker, setShowSystemPicker] = useState(false)
    const [systemSearch, setSystemSearch] = useState('')
    const [systemLoading, setSystemLoading] = useState(false)
    const [systemError, setSystemError] = useState<string | null>(null)
    const [systemDocuments, setSystemDocuments] = useState<FolderDocumentResponse[]>([])
    const [systemFolders, setSystemFolders] = useState<FolderResponse[]>([])
    const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([])
    const [selectedFolderIds, setSelectedFolderIds] = useState<string[]>([])
    const [activeTab, setActiveTab] = useState<'documents' | 'folders'>('documents')
    const fileInputRef = useRef<HTMLInputElement>(null)
    const textareaRef = useRef<HTMLTextAreaElement>(null)

    const uploadStats = attachments.reduce(
        (acc, att) => {
            acc.total += 1
            if (att.status === 'uploading') acc.uploading += 1
            else if (att.status === 'processing') acc.processing += 1
            else if (att.status === 'completed') acc.completed += 1
            else if (att.status === 'failed') acc.failed += 1
            return acc
        },
        { total: 0, uploading: 0, processing: 0, completed: 0, failed: 0 }
    )

    const uploadReadinessPercent = uploadStats.total > 0
        ? Math.round((uploadStats.completed / uploadStats.total) * 100)
        : 0

    const uploadReadinessLabel = (() => {
        if (uploadStats.total === 0) return 'Chưa có file nào được tải lên'
        if (uploadStats.failed > 0 && uploadStats.completed === 0 && uploadStats.processing === 0 && uploadStats.uploading === 0) {
            return 'Có file tải lên bị lỗi'
        }
        if (uploadStats.completed === uploadStats.total) return 'Tất cả file đã sẵn sàng để tìm kiếm'
        if (uploadStats.processing > 0) return 'Đang phân tích tài liệu để sẵn sàng tìm kiếm'
        if (uploadStats.uploading > 0) return 'Đang tải file lên'
        return 'Đang cập nhật trạng thái file'
    })()

    const flattenFolders = useCallback((folders: FolderResponse[]): FolderResponse[] => {
        const flat: FolderResponse[] = []

        const walk = (items: FolderResponse[]) => {
            items.forEach((folder) => {
                flat.push(folder)
                if (folder.sub_folders?.length) {
                    walk(folder.sub_folders)
                }
            })
        }

        walk(folders)
        return flat
    }, [])

    const loadSystemAttachments = useCallback(async () => {
        try {
            setSystemLoading(true)
            setSystemError(null)

            // ✅ Call endpoint that filters by user role & permissions
            // Only runs on client-side
            const data = await fetchAvailableAttachments()

            setSystemFolders(flattenFolders(data.folders))
            setSystemDocuments(data.documents)

            console.log(`📎 Loaded ${data.documents.length} accessible documents and ${data.folders.length} accessible folders`)
        } catch (error) {
            console.error('Failed to load available attachments:', error)
            setSystemError('Không thể tải danh sách tài liệu/thư mục có quyền truy cập')
        } finally {
            setSystemLoading(false)
        }
    }, [flattenFolders])

    // Only load attachments when picker is shown (lazy load, client-side only)
    useEffect(() => {
        if (showSystemPicker && systemDocuments.length === 0 && systemFolders.length === 0) {
            // Use setTimeout to ensure running after hydration
            const timer = setTimeout(() => {
                loadSystemAttachments()
            }, 0)
            return () => clearTimeout(timer)
        }
    }, [showSystemPicker, loadSystemAttachments, systemDocuments.length, systemFolders.length])

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px'
        }
    }, [message])

    const handleSend = () => {
        if (!message.trim() || isLoading || disabled) return

        // Chỉ gửi những file đã hoàn thành xử lý
        const completedUploads = attachments.filter(att => att.status === 'completed' && att.documentId)
        const completedUploadIds = completedUploads.map(att => att.documentId!)

        onSendMessage?.(message, {
            documentIds: [...selectedDocumentIds, ...completedUploadIds],
            folderIds: selectedFolderIds,
        })

        setMessage('')
        // Giữ nguyên attachment để user có thể hỏi nhiều câu liên tiếp trên cùng bộ file
        // Chỉ đóng picker / reset nhập liệu tạm thời, không xoá selection sau khi gửi
        setShowSystemPicker(false)
        setSystemSearch('')

        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
        }
    }

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.currentTarget.files
        if (!files) return

        const fileArray = Array.from(files)

        for (let i = 0; i < fileArray.length; i++) {
            const file = fileArray[i]
            const uploadId = `${Date.now()}-${i}`

            // 1. Thêm vào state với trạng thái đang upload
            const newUpload: ChatUploadAttachment = {
                id: uploadId,
                name: file.name,
                size: file.size,
                type: file.type,
                progress: 0,
                status: 'uploading',
                statusText: 'Đang tải lên...'
            }

            setAttachments((prev) => [...prev, newUpload].slice(0, 10))

            try {
                // 2. Bắt đầu upload
                const document = await uploadDocument(file, {
                    accessScope: 'personal',
                    onProgress: (percent) => {
                        setAttachments(prev => prev.map(att =>
                            att.id === uploadId ? { ...att, progress: percent } : att
                        ))
                    }
                })

                // 3. Chuyển sang trạng thái đang xử lý (Parsing/Embedding)
                setAttachments(prev => prev.map(att =>
                    att.id === uploadId ? {
                        ...att,
                        status: 'processing',
                        statusText: 'Đang phân tích...',
                        documentId: document.id
                    } : att
                ))

                // 4. Polling trạng thái xử lý từ backend
                let isDone = false
                let retryCount = 0
                const maxRetries = 120 // 4 phút (2s × 120 = 240s)
                let pollDelay = 1000 // Start with 1 second

                while (!isDone && retryCount < maxRetries) {
                    await new Promise(resolve => setTimeout(resolve, pollDelay))
                    retryCount++
                    // Gradually increase poll delay (1s -> 2s -> 3s -> 4s max)
                    pollDelay = Math.min(pollDelay + 500, 4000)

                    try {
                        const statusData = await getDocumentStatus(document.id)
                        const docStatus = statusData.data?.document_status

                        if (docStatus === 'completed') {
                            setAttachments(prev => prev.map(att =>
                                att.id === uploadId ? {
                                    ...att,
                                    status: 'completed',
                                    statusText: 'Sẵn sàng',
                                    progress: 100
                                } : att
                            ))
                            isDone = true
                        } else if (docStatus === 'failed') {
                            throw new Error('Xử lý thất bại')
                        } else {
                            // Cập nhật text chi tiết nếu có
                            const chunks = statusData.data?.chunk_processing_status
                            if (chunks) {
                                const percent = Math.round((chunks.completed_chunks / (chunks.total_chunks || 1)) * 100)
                                setAttachments(prev => prev.map(att =>
                                    att.id === uploadId ? {
                                        ...att,
                                        statusText: `Đang phân tích (${percent}%)`
                                    } : att
                                ))
                            }
                        }
                    } catch (err) {
                        console.error('Polling error:', err)
                    }
                }

                if (!isDone) {
                    throw new Error('Hết thời gian chờ xử lý')
                }

            } catch (error) {
                console.error('Upload error:', error)
                setAttachments(prev => prev.map(att =>
                    att.id === uploadId ? {
                        ...att,
                        status: 'failed',
                        statusText: 'Lỗi xử lý'
                    } : att
                ))
            }
        }

        // Reset file input
        if (fileInputRef.current) fileInputRef.current.value = ''
    }

    const removeAttachment = useCallback((id: string) => {
        setAttachments((prev) => prev.filter((att) => att.id !== id))
    }, [])

    const toggleDocument = (documentId: string) => {
        setSelectedDocumentIds((prev) =>
            prev.includes(documentId)
                ? prev.filter((id) => id !== documentId)
                : [...prev, documentId]
        )
    }

    const toggleFolder = (folderId: string) => {
        setSelectedFolderIds((prev) =>
            prev.includes(folderId)
                ? prev.filter((id) => id !== folderId)
                : [...prev, folderId]
        )
    }

    const clearSystemAttachments = useCallback(() => {
        setSelectedDocumentIds([])
        setSelectedFolderIds([])
    }, [])

    useEffect(() => {
        const selectedDocuments: ChatSelectedResourceItem[] = selectedDocumentIds.map((id) => {
            const doc = systemDocuments.find((item) => item.id === id)
            return {
                id,
                name: doc?.original_name || doc?.filename || 'Tài liệu không xác định',
                detail: doc?.file_type,
            }
        })

        const selectedFolders: ChatSelectedResourceItem[] = selectedFolderIds.map((id) => {
            const folder = systemFolders.find((item) => item.id === id)
            return {
                id,
                name: folder?.name || 'Thư mục không xác định',
                detail: folder?.access_scope,
            }
        })

        onAttachmentStateChange?.({
            uploads: attachments,
            selectedDocuments,
            selectedFolders,
            totalSelected: attachments.length + selectedDocuments.length + selectedFolders.length,
            removeUpload: removeAttachment,
            removeDocument: (id: string) => {
                setSelectedDocumentIds((prev) => prev.filter((item) => item !== id))
            },
            removeFolder: (id: string) => {
                setSelectedFolderIds((prev) => prev.filter((item) => item !== id))
            },
            clearAll: clearSystemAttachments,
        })
    }, [
        attachments,
        clearSystemAttachments,
        onAttachmentStateChange,
        removeAttachment,
        selectedDocumentIds,
        selectedFolderIds,
        systemDocuments,
        systemFolders,
    ])

    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes'
        const k = 1024
        const sizes = ['Bytes', 'KB', 'MB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }

    return (
        <div className="p-6 md:p-8 bg-gradient-to-t from-surface via-surface to-transparent border-t border-outline-variant/10">
            <div className="max-w-4xl mx-auto relative group">
                {/* Input Container */}
                <div className="relative bg-white dark:bg-slate-800 shadow-2xl shadow-slate-200/50 dark:shadow-slate-950/50 rounded-2xl border border-outline-variant/10 dark:border-slate-700/30 p-2 flex items-end gap-2 focus-within:ring-2 focus-within:ring-primary/10 focus-within:border-primary/20 transition-all">
                    {/* Local file upload */}
                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isLoading || disabled}
                        className="flex-shrink-0 p-2 text-slate-400 hover:text-primary hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Tải file từ máy"
                    >
                        <Paperclip size={20} />
                    </button>

                    {/* System attachment picker */}
                    <button
                        type="button"
                        onClick={() => setShowSystemPicker(true)}
                        disabled={isLoading || disabled}
                        className="flex-shrink-0 p-2 text-slate-400 hover:text-primary hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Đính kèm tài liệu/thư mục trong hệ thống"
                    >
                        <FolderOpen size={20} />
                    </button>

                    <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        onChange={handleFileChange}
                        className="hidden"
                        accept=".pdf,.doc,.docx,.txt,.xlsx,.csv"
                    />

                    {/* Textarea */}
                    <textarea
                        ref={textareaRef}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault()
                                handleSend()
                            }
                        }}
                        placeholder={placeholder}
                        disabled={isLoading || disabled}
                        className="flex-1 bg-transparent text-on-surface dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 resize-none outline-none text-sm leading-relaxed max-h-48 min-h-[44px] py-2 px-2"
                        rows={1}
                    />

                    {/* Send Button */}
                    <button
                        onClick={handleSend}
                        disabled={
                            !message.trim() ||
                            isLoading ||
                            disabled
                        }
                        className="flex-shrink-0 p-2.5 bg-gradient-to-br from-primary to-primary-container text-on-primary rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg hover:shadow-primary/30 active:scale-95 flex items-center justify-center"
                        title="Gửi (Enter hoặc Shift+Enter)"
                    >
                        <Send size={20} />
                    </button>
                </div>

                {/* Upload readiness bar */}
                {attachments.length > 0 && (
                    <div className="mt-3 px-2">
                        <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white/90 dark:bg-slate-800/80 px-4 py-3 shadow-sm">
                            <div className="flex items-start justify-between gap-3">

                                <div className="shrink-0 text-right">
                                    <div className="text-lg font-extrabold text-primary">{uploadReadinessPercent}%</div>
                                    <div className="text-[10px] uppercase tracking-widest text-slate-400">Sẵn sàng</div>
                                </div>
                            </div>

                            <div className="mt-3 h-2 rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden">
                                <div
                                    className="h-full rounded-full bg-gradient-to-r from-primary via-amber-500 to-emerald-500 transition-all duration-300"
                                    style={{ width: `${uploadReadinessPercent}%` }}
                                />
                            </div>
                        </div>
                    </div>
                )}

                {/* Uploads Preview with Status */}
                {attachments.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2 px-2">
                        {attachments.map((att) => (
                            <div key={att.id} className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5 flex gap-2 items-start">
                                <div className="flex flex-col max-w-[150px]">
                                    <span className="font-medium truncate" title={att.name}>{att.name}</span>
                                    <div className="flex items-center gap-2 mt-0.5">
                                        {att.status === 'uploading' || att.status === 'processing' ? (
                                            <div className="w-12 h-1 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-primary transition-all duration-300"
                                                    style={{ width: `${att.progress || 0}%` }}
                                                />
                                            </div>
                                        ) : att.status === 'completed' ? (
                                            <Check size={10} className="text-success" />
                                        ) : null}
                                        <span className="text-[9px] opacity-70 uppercase tracking-tight">{att.statusText}</span>
                                    </div>
                                </div>
                                <button
                                    onClick={() => removeAttachment(att.id)}
                                    className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-full transition-colors"
                                >
                                    <X size={14} />
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                {/* Help Text */}
                <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-2 px-2">
                    Nhấn <kbd className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-slate-700 dark:text-slate-300">Enter</kbd> để gửi, <kbd className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-slate-700 dark:text-slate-300">Shift+Enter</kbd> để xuống dòng
                </p>
            </div>

            {showSystemPicker && (
                <div className="fixed inset-0 z-50 bg-slate-950/40 backdrop-blur-sm flex items-center justify-center p-4">
                    <div className="w-full max-w-5xl bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden max-h-[85vh] flex flex-col">
                        <div className="flex items-start justify-between gap-4 px-5 py-4 border-b border-slate-100 dark:border-slate-800">
                            <div className="min-w-0">
                                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">Đính kèm từ hệ thống</h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Chọn tài liệu hoặc thư mục có sẵn trong kho tri thức, không phải file từ máy.</p>
                            </div>
                            {activeTab !== 'documents' && (
                                <button
                                    type="button"
                                    onClick={() => setShowSystemPicker(false)}
                                    className="p-2 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors shrink-0"
                                    title="Đóng"
                                >
                                    <X size={18} />
                                </button>
                            )}
                        </div>

                        <div className="p-5 space-y-4 flex-1 overflow-hidden flex flex-col">
                            <div className="flex items-center gap-2 rounded-2xl bg-slate-50 dark:bg-slate-800 p-2">
                                <button
                                    type="button"
                                    onClick={() => setActiveTab('documents')}
                                    className={`px-3 py-2 rounded-xl text-xs font-bold transition-colors ${activeTab === 'documents'
                                        ? 'bg-white dark:bg-slate-900 text-primary shadow-sm'
                                        : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-200'
                                        }`}
                                >
                                    Tài liệu ({systemDocuments.length})
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setActiveTab('folders')}
                                    className={`px-3 py-2 rounded-xl text-xs font-bold transition-colors ${activeTab === 'folders'
                                        ? 'bg-white dark:bg-slate-900 text-primary shadow-sm'
                                        : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-200'
                                        }`}
                                >
                                    Thư mục ({systemFolders.length})
                                </button>
                                <div className="flex-1" />
                                <button
                                    type="button"
                                    onClick={clearSystemAttachments}
                                    className="text-xs font-semibold text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                                >
                                    Bỏ chọn
                                </button>
                            </div>

                            <div className="relative shrink-0">
                                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                                <input
                                    value={systemSearch}
                                    onChange={(e) => setSystemSearch(e.target.value)}
                                    placeholder="Tìm kiếm trong hệ thống..."
                                    className="w-full pl-9 pr-3 py-3 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm text-slate-700 dark:text-slate-100 outline-none focus:ring-2 focus:ring-primary/10"
                                />
                            </div>

                            {systemLoading ? (
                                <div className="py-14 text-center text-sm text-slate-500">Đang tải dữ liệu hệ thống...</div>
                            ) : systemError ? (
                                <div className="py-14 text-center text-sm text-red-500">{systemError}</div>
                            ) : (
                                <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.8fr)] gap-4 flex-1 min-h-0 overflow-hidden">
                                    <div className="min-h-0 overflow-hidden">
                                        {activeTab === 'documents' ? (
                                            <div className="h-full max-h-[calc(85vh-280px)] overflow-y-auto space-y-2 pr-1">
                                                {systemDocuments
                                                    .filter((doc) => {
                                                        const needle = systemSearch.toLowerCase()
                                                        return !needle || [doc.original_name, doc.filename, doc.file_type].some((value) =>
                                                            (value || '').toLowerCase().includes(needle)
                                                        )
                                                    })
                                                    .map((doc) => {
                                                        const displayName = doc.original_name || doc.filename
                                                        const isSelected = selectedDocumentIds.includes(doc.id)

                                                        return (
                                                            <button
                                                                key={doc.id}
                                                                type="button"
                                                                onClick={() => toggleDocument(doc.id)}
                                                                className={`w-full text-left p-3 rounded-2xl border transition-colors ${isSelected
                                                                    ? 'border-primary/30 bg-primary/5'
                                                                    : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
                                                                    }`}
                                                            >
                                                                <div className="flex items-start gap-3">
                                                                    <div className="w-9 h-9 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center shrink-0">
                                                                        <span className="material-symbols-outlined text-base text-slate-500">description</span>
                                                                    </div>
                                                                    <div className="min-w-0 flex-1">
                                                                        <div className="flex items-center gap-2">
                                                                            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">{displayName}</p>
                                                                            {isSelected && <Check size={14} className="text-primary shrink-0" />}
                                                                        </div>
                                                                        <p className="text-[11px] text-slate-500 truncate mt-1">{doc.file_type} • {doc.access_scope}</p>
                                                                    </div>
                                                                </div>
                                                            </button>
                                                        )
                                                    })}
                                                {systemDocuments.filter((doc) => {
                                                    const needle = systemSearch.toLowerCase()
                                                    return !needle || [doc.original_name, doc.filename, doc.file_type].some((value) =>
                                                        (value || '').toLowerCase().includes(needle)
                                                    )
                                                }).length === 0 && (
                                                        <div className="py-14 text-center text-sm text-slate-500">Không tìm thấy tài liệu phù hợp.</div>
                                                    )}
                                            </div>
                                        ) : (
                                            <div className="h-full max-h-[calc(85vh-280px)] overflow-y-auto space-y-2 pr-1">
                                                {systemFolders
                                                    .filter((folder) => {
                                                        const needle = systemSearch.toLowerCase()
                                                        return !needle || [folder.name, folder.description || '', folder.access_scope].some((value) =>
                                                            value.toLowerCase().includes(needle)
                                                        )
                                                    })
                                                    .map((folder) => {
                                                        const isSelected = selectedFolderIds.includes(folder.id)

                                                        return (
                                                            <button
                                                                key={folder.id}
                                                                type="button"
                                                                onClick={() => toggleFolder(folder.id)}
                                                                className={`w-full text-left p-3 rounded-2xl border transition-colors ${isSelected
                                                                    ? 'border-primary/30 bg-primary/5'
                                                                    : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
                                                                    }`}
                                                            >
                                                                <div className="flex items-start gap-3">
                                                                    <div className="w-9 h-9 rounded-xl bg-amber-50 flex items-center justify-center shrink-0">
                                                                        <FolderOpen size={16} className="text-amber-600" />
                                                                    </div>
                                                                    <div className="min-w-0 flex-1">
                                                                        <div className="flex items-center gap-2">
                                                                            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">{folder.name}</p>
                                                                            {isSelected && <Check size={14} className="text-primary shrink-0" />}
                                                                        </div>
                                                                        <p className="text-[11px] text-slate-500 truncate mt-1 capitalize">{folder.access_scope}</p>
                                                                    </div>
                                                                </div>
                                                            </button>
                                                        )
                                                    })}
                                                {systemFolders.filter((folder) => {
                                                    const needle = systemSearch.toLowerCase()
                                                    return !needle || [folder.name, folder.description || '', folder.access_scope].some((value) =>
                                                        value.toLowerCase().includes(needle)
                                                    )
                                                }).length === 0 && (
                                                        <div className="py-14 text-center text-sm text-slate-500">Không tìm thấy thư mục phù hợp.</div>
                                                    )}
                                            </div>
                                        )}
                                    </div>

                                    <div className="rounded-3xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-4 space-y-3 min-h-0 flex flex-col">
                                        <div className="shrink-0">
                                            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Đã chọn</p>
                                            <p className="text-sm text-slate-700 dark:text-slate-200 mt-1">
                                                {selectedDocumentIds.length} tài liệu, {selectedFolderIds.length} thư mục
                                            </p>
                                        </div>

                                        <div className="space-y-2 overflow-y-auto flex-1 min-h-0 pr-1">
                                            {selectedDocumentIds.map((id) => {
                                                const doc = systemDocuments.find((item) => item.id === id)
                                                if (!doc) return null
                                                return (
                                                    <div key={id} className="flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-xs">
                                                        <span className="truncate text-slate-700 dark:text-slate-200">{doc.original_name || doc.filename}</span>
                                                        <button type="button" onClick={() => toggleDocument(id)} className="text-slate-400 hover:text-red-500">
                                                            <X size={14} />
                                                        </button>
                                                    </div>
                                                )
                                            })}
                                            {selectedFolderIds.map((id) => {
                                                const folder = systemFolders.find((item) => item.id === id)
                                                if (!folder) return null
                                                return (
                                                    <div key={id} className="flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-xs">
                                                        <span className="truncate text-slate-700 dark:text-slate-200">{folder.name}</span>
                                                        <button type="button" onClick={() => toggleFolder(id)} className="text-slate-400 hover:text-red-500">
                                                            <X size={14} />
                                                        </button>
                                                    </div>
                                                )
                                            })}
                                            {selectedDocumentIds.length === 0 && selectedFolderIds.length === 0 && (
                                                <div className="text-xs text-slate-500 py-6 text-center">Chưa chọn gì.</div>
                                            )}
                                        </div>

                                        <button
                                            type="button"
                                            onClick={() => setShowSystemPicker(false)}
                                            className="w-full py-3 rounded-2xl bg-primary text-on-primary text-sm font-bold hover:opacity-90 transition-colors"
                                        >
                                            Áp dụng
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
