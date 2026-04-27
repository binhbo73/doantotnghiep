'use client'

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Paperclip, X, FolderOpen, Search, Check } from 'lucide-react'
import { fetchAllDocuments, fetchAllFolders, FolderDocumentResponse, FolderResponse } from '@/services/folder'
import { ConversationAttachmentPayload } from '@/services/chatService'

interface Attachment {
    id: string
    name: string
    size: number
    type: string
}

interface ChatInputProps {
    onSendMessage?: (message: string, attachments?: ConversationAttachmentPayload) => void
    placeholder?: string
    isLoading?: boolean
    disabled?: boolean
}

export const ChatInput: React.FC<ChatInputProps> = ({
    onSendMessage,
    placeholder = 'Hỏi tôi bất cứ điều gì về tài liệu và tri thức nội bộ...',
    isLoading = false,
    disabled = false,
}) => {
    const [message, setMessage] = useState('')
    const [attachments, setAttachments] = useState<Attachment[]>([])
    const [showAttachments, setShowAttachments] = useState(false)
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

            const [folderData, documentData] = await Promise.all([
                fetchAllFolders(),
                fetchAllDocuments({ page_size: 100 }),
            ])

            setSystemFolders(flattenFolders(folderData))
            setSystemDocuments(documentData.items)
        } catch (error) {
            console.error('Failed to load system attachments:', error)
            setSystemError('Không thể tải danh sách tài liệu/thư mục trong hệ thống')
        } finally {
            setSystemLoading(false)
        }
    }, [flattenFolders])

    useEffect(() => {
        if (showSystemPicker && systemDocuments.length === 0 && systemFolders.length === 0) {
            loadSystemAttachments()
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

        onSendMessage?.(message, {
            documentIds: selectedDocumentIds,
            folderIds: selectedFolderIds,
        })
        setMessage('')
        setAttachments([])
        setShowAttachments(false)
        setShowSystemPicker(false)
        setSystemSearch('')

        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
        }
    }

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.currentTarget.files
        if (!files) return

        const newAttachments: Attachment[] = []
        for (let i = 0; i < files.length; i++) {
            const file = files[i]
            newAttachments.push({
                id: `${Date.now()}-${i}`,
                name: file.name,
                size: file.size,
                type: file.type,
            })
        }

        setAttachments((prev) => [...prev, ...newAttachments].slice(0, 5)) // Max 5 files
        setShowAttachments(true)
    }

    const removeAttachment = (id: string) => {
        setAttachments((prev) => prev.filter((att) => att.id !== id))
    }

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

    const clearSystemAttachments = () => {
        setSelectedDocumentIds([])
        setSelectedFolderIds([])
    }

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
                {/* Attachments Preview */}
                {showAttachments && attachments.length > 0 && (
                    <div className="absolute -top-12 left-0 flex gap-2 flex-wrap">
                        {attachments.map((att) => (
                            <div
                                key={att.id}
                                className="bg-white/90 dark:bg-slate-800/90 backdrop-blur shadow-sm border border-orange-100 dark:border-orange-900/30 px-3 py-1.5 rounded-full flex items-center gap-2 text-xs font-bold text-orange-600 dark:text-orange-400 hover:bg-orange-50 dark:hover:bg-orange-900/20 transition-colors"
                            >
                                <Paperclip size={14} className="shrink-0" />
                                <span className="truncate max-w-[120px]" title={att.name}>
                                    {att.name}
                                </span>
                                <button
                                    onClick={() => removeAttachment(att.id)}
                                    className="text-orange-600 dark:text-orange-400 hover:text-orange-700 dark:hover:text-orange-300 transition-colors"
                                >
                                    <X size={14} />
                                </button>
                            </div>
                        ))}
                    </div>
                )}

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
                        disabled={!message.trim() || isLoading || disabled}
                        className="flex-shrink-0 p-2.5 bg-gradient-to-br from-primary to-primary-container text-on-primary rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg hover:shadow-primary/30 active:scale-95 flex items-center justify-center"
                        title="Gửi (Enter hoặc Shift+Enter)"
                    >
                        <Send size={20} />
                    </button>
                </div>

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
