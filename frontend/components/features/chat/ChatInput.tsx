'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, X } from 'lucide-react'

interface Attachment {
    id: string
    name: string
    size: number
    type: string
}

interface ChatInputProps {
    onSendMessage?: (message: string, attachments?: Attachment[]) => void
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
    const fileInputRef = useRef<HTMLInputElement>(null)
    const textareaRef = useRef<HTMLTextAreaElement>(null)

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px'
        }
    }, [message])

    const handleSend = () => {
        if (!message.trim() || isLoading || disabled) return

        onSendMessage?.(message, attachments.length > 0 ? attachments : undefined)
        setMessage('')
        setAttachments([])
        setShowAttachments(false)

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
                    {/* Attachment Button */}
                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isLoading || disabled}
                        className="flex-shrink-0 p-2 text-slate-400 hover:text-primary hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Đính kèm tệp"
                    >
                        <Paperclip size={20} />
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
        </div>
    )
}
