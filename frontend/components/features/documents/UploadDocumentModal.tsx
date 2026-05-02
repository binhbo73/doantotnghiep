'use client'

import React, { useState, useEffect } from 'react'
import { env } from '@/config/environment'
import { uploadService } from '@/services/upload'
import { useDepartments } from '@/hooks/useDepartments'
import { useDocumentStore } from '@/hooks/useDocumentStore'

interface UploadDocumentModalProps {
    isOpen: boolean
    onClose: () => void
    onSuccess?: () => void
}

export function UploadDocumentModal({ isOpen, onClose, onSuccess }: UploadDocumentModalProps) {
    const { tree } = useDocumentStore()
    const { departments } = useDepartments()

    const [file, setFile] = useState<File | null>(null)
    const [accessScope, setAccessScope] = useState<'company' | 'department' | 'personal'>('company')
    const [departmentId, setDepartmentId] = useState<string>('')
    const [folderId, setFolderId] = useState<string>('')
    const [description, setDescription] = useState('')
    const [tagsInput, setTagsInput] = useState('')

    const [isUploading, setIsUploading] = useState(false)
    const [progress, setProgress] = useState(0)
    const [error, setError] = useState<string | null>(null)
    const maxUploadMb = Math.round(env.maxUploadSize / 1024 / 1024)

    const validateFile = (selectedFile: File): boolean => {
        if (selectedFile.size > env.maxUploadSize) {
            setError(`File quá lớn. Tối đa ${maxUploadMb}MB.`)
            return false
        }

        return true
    }

    // Reset state when modal opens
    useEffect(() => {
        if (isOpen) {
            setFile(null)
            setAccessScope('company')
            setDepartmentId('')
            setFolderId('')
            setDescription('')
            setTagsInput('')
            setProgress(0)
            setError(null)
            setIsUploading(false)
        }
    }, [isOpen])

    // Reset folder selection when department changes
    useEffect(() => {
        setFolderId('')
    }, [departmentId])

    // Flatten folder tree for select options
    const flattenTree = (nodes: typeof tree, depth = 0): { id: string, name: string, depth: number, department_id: string | null }[] => {
        let result: { id: string, name: string, depth: number, department_id: string | null }[] = []
        for (const node of nodes) {
            result.push({ id: node.folder.id, name: node.folder.name, depth, department_id: node.folder.department_id })
            if (node.children && node.children.length > 0) {
                result = result.concat(flattenTree(node.children, depth + 1))
            }
        }
        return result
    }

    const foldersList = flattenTree(tree)
    const displayFoldersList = departmentId
        ? foldersList.filter(f => f.department_id === departmentId)
        : foldersList

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const selectedFile = e.target.files[0]
            if (validateFile(selectedFile)) {
                setFile(selectedFile)
                setError(null)
            }
        }
    }

    const handleUpload = async () => {
        if (!file) {
            setError('Vui lòng chọn một file.')
            return
        }

        if (!validateFile(file)) {
            return
        }

        setIsUploading(true)
        setError(null)

        try {
            const tagsArray = tagsInput.split(',').map(t => t.trim()).filter(t => t !== '')

            await uploadService.uploadFile(file, {
                folderId: folderId || undefined,
                departmentId: departmentId || undefined,
                accessScope,
                description: description || undefined,
                tags: tagsArray,
                onProgress: (prog) => {
                    setProgress(prog.percentage)
                }
            })

            if (onSuccess) onSuccess()
            onClose()
        } catch (err: any) {
            setError(err.message || 'Upload thất bại.')
        } finally {
            setIsUploading(false)
        }
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                    <h2 className="text-lg font-bold text-slate-800">Tải lên Tài liệu</h2>
                    <button
                        onClick={onClose}
                        disabled={isUploading}
                        className="p-2 hover:bg-slate-100 rounded-full transition-colors text-slate-500 disabled:opacity-50"
                    >
                        <span className="material-symbols-outlined text-xl">close</span>
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 overflow-y-auto flex-1 space-y-5">
                    {error && (
                        <div className="p-3 bg-red-50 text-red-600 rounded-xl text-sm border border-red-100">
                            {error}
                        </div>
                    )}

                    {/* Drag and Drop File Input */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Chọn File <span className="text-red-500">*</span>
                        </label>
                        <div
                            className={`relative border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center transition-all cursor-pointer bg-slate-50 hover:bg-[#fff3e0] hover:border-[#9d4300]/50 ${file ? 'border-[#9d4300] bg-[#fff3e0]' : 'border-slate-300'}`}
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={(e) => {
                                e.preventDefault()
                                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                                    const droppedFile = e.dataTransfer.files[0]
                                    if (validateFile(droppedFile)) {
                                        setFile(droppedFile)
                                        setError(null)
                                    }
                                }
                            }}
                        >
                            <input
                                type="file"
                                accept=".pdf,.doc,.docx,.txt,.md,.xlsx,.xls"
                                onChange={handleFileChange}
                                disabled={isUploading}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
                            />
                            {file ? (
                                <>
                                    <div className="w-14 h-14 bg-[#9d4300] text-white rounded-2xl flex items-center justify-center mb-3 shadow-md shadow-[#9d4300]/20">
                                        <span className="material-symbols-outlined text-3xl">description</span>
                                    </div>
                                    <p className="text-sm font-bold text-slate-800 text-center break-all px-4">{file.name}</p>
                                    <p className="text-xs text-[#9d4300] font-semibold mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                                </>
                            ) : (
                                <>
                                    <div className="w-14 h-14 bg-white border border-slate-200 text-[#9d4300] rounded-2xl flex items-center justify-center mb-3 shadow-sm">
                                        <span className="material-symbols-outlined text-3xl">cloud_upload</span>
                                    </div>
                                    <p className="text-sm font-bold text-slate-700 text-center">Kéo thả file vào đây hoặc nhấn để chọn</p>
                                    <p className="text-xs text-slate-400 mt-1 font-medium">Hỗ trợ PDF, DOCX, TXT, MD, XLSX - tối đa {maxUploadMb}MB</p>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Access Scope */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Phạm vi truy cập
                        </label>
                        <select
                            value={accessScope}
                            onChange={(e) => setAccessScope(e.target.value as any)}
                            disabled={isUploading}
                            className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300] transition-colors"
                        >
                            <option value="company">Toàn công ty</option>
                            <option value="department">Phòng ban</option>
                            <option value="personal">Cá nhân</option>
                        </select>
                    </div>

                    {/* Department */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Phòng ban {accessScope === 'department' ? <span className="text-red-500">*</span> : '(Tùy chọn)'}
                        </label>
                        <select
                            value={departmentId}
                            onChange={(e) => setDepartmentId(e.target.value)}
                            disabled={isUploading}
                            className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300] transition-colors"
                        >
                            <option value="">-- Chọn phòng ban --</option>
                            {departments.map((dept, index) => (
                                <option key={`${dept.id}-${index}`} value={dept.id}>{dept.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Folder */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Thư mục (Tùy chọn)
                        </label>
                        <select
                            value={folderId}
                            onChange={(e) => setFolderId(e.target.value)}
                            disabled={isUploading}
                            className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300] transition-colors"
                        >
                            <option value="">-- Không chọn (Gốc) --</option>
                            {displayFoldersList.map((folder, index) => (
                                <option key={`${folder.id}-${index}`} value={folder.id}>
                                    {'\u00A0'.repeat(folder.depth * 4)}
                                    {folder.depth > 0 ? '↳ ' : ''}
                                    {folder.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Description */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Mô tả
                        </label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            disabled={isUploading}
                            rows={3}
                            placeholder="Nhập mô tả tài liệu..."
                            className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300] transition-colors resize-none"
                        />
                    </div>

                    {/* Tags */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Tags (phân cách bằng dấu phẩy)
                        </label>
                        <input
                            type="text"
                            value={tagsInput}
                            onChange={(e) => setTagsInput(e.target.value)}
                            disabled={isUploading}
                            placeholder="vd: quy trình, kỹ thuật, 2024"
                            className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300] transition-colors"
                        />
                    </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex items-center justify-end gap-3">
                    {isUploading && (
                        <div className="flex-1 mr-4 flex items-center gap-3">
                            <div className="h-2 flex-1 bg-slate-200 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-[#9d4300] transition-all duration-300"
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                            <span className="text-xs font-bold text-slate-500">{progress}%</span>
                        </div>
                    )}
                    <button
                        onClick={onClose}
                        disabled={isUploading}
                        className="px-5 py-2.5 text-sm font-bold text-slate-600 hover:bg-slate-200 rounded-xl transition-colors disabled:opacity-50"
                    >
                        Hủy
                    </button>
                    <button
                        onClick={handleUpload}
                        disabled={!file || isUploading || (accessScope === 'department' && !departmentId)}
                        className="px-5 py-2.5 text-sm font-bold text-white bg-[#9d4300] hover:bg-[#b75b00] rounded-xl shadow-md shadow-[#9d4300]/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {isUploading ? (
                            <>
                                <span className="material-symbols-outlined animate-spin text-sm">sync</span>
                                Đang tải...
                            </>
                        ) : (
                            <>
                                <span className="material-symbols-outlined text-sm">upload</span>
                                Tải lên
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    )
}
