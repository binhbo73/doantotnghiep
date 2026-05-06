'use client'

import React, { useState, useEffect, useRef } from 'react'
import { env } from '@/config/environment'
import { uploadService } from '@/services/upload'
import { useDepartments } from '@/hooks/useDepartments'
import { useDocumentStore } from '@/hooks/useDocumentStore'
import { useRBAC } from '@/hooks/useRBAC'
import { useAuthContext } from '@/context'

interface UploadDocumentModalProps {
    isOpen: boolean
    onClose: () => void
    onSuccess?: () => void
    defaultAccessScope?: 'company' | 'department' | 'personal'
    allowedScopes?: Array<'company' | 'department' | 'personal'>
}

export function UploadDocumentModal({
    isOpen,
    onClose,
    onSuccess,
    defaultAccessScope,
    allowedScopes: allowedScopesProp,
}: UploadDocumentModalProps) {
    const { tree } = useDocumentStore()
    const { departments } = useDepartments()
    const { user } = useAuthContext()
    const { isAdmin } = useRBAC()
    const isAdminUser = isAdmin()
    const userDepartmentId = user?.department_id || ''

    const roleAllowedScopes = isAdminUser
        ? ['personal', 'department', 'company']
        : ['department', 'company']

    const allowedScopes = allowedScopesProp ?? roleAllowedScopes

    const [file, setFile] = useState<File | null>(null)
    const [accessScope, setAccessScope] = useState<'company' | 'department' | 'personal'>(
        defaultAccessScope ?? (isAdminUser ? 'company' : 'department')
    )
    const [departmentId, setDepartmentId] = useState<string>(userDepartmentId)
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
            setAccessScope(defaultAccessScope ?? (isAdminUser ? 'company' : 'department'))
            setDepartmentId(userDepartmentId)
            setFolderId('')
            setDescription('')
            setTagsInput('')
            setProgress(0)
            setError(null)
            setIsUploading(false)
        }
    }, [isOpen, defaultAccessScope, isAdminUser, userDepartmentId])

    // Flatten folder tree for select options
    const flattenTree = (
        nodes: typeof tree,
        depth = 0
    ): {
        id: string
        name: string
        depth: number
        department_id: string | null
        access_scope: 'company' | 'department' | 'personal'
    }[] => {
        let result: {
            id: string
            name: string
            depth: number
            department_id: string | null
            access_scope: 'company' | 'department' | 'personal'
        }[] = []
        for (const node of nodes) {
            result.push({
                id: node.folder.id,
                name: node.folder.name,
                depth,
                department_id: node.folder.department_id,
                access_scope: node.folder.access_scope,
            })
            if (node.children && node.children.length > 0) {
                result = result.concat(flattenTree(node.children, depth + 1))
            }
        }
        return result
    }

    const foldersList = flattenTree(tree)
    const selectedFolder = foldersList.find(f => f.id === folderId)

    // Scope-compatible folder filtering for Direction 2 behavior
    const displayFoldersList = foldersList.filter(f => {
        if (allowedScopes.length === 1 && allowedScopes[0] === 'personal') {
            return f.access_scope === 'personal'
        }

        if (accessScope === 'company') {
            // company-scoped documents cannot go into department/personal folders
            return f.access_scope === 'company'
        }
        if (accessScope === 'department') {
            // department-scoped documents can go to company or department folders
            return f.access_scope !== 'personal'
        }
        // personal docs can exist in any folder type (with backend validation)
        return true
    })

    // Auto-map department when user picks a department folder in department scope.
    useEffect(() => {
        if (!folderId || !selectedFolder) return
        if (accessScope === 'department' && selectedFolder.access_scope === 'department' && selectedFolder.department_id) {
            setDepartmentId(selectedFolder.department_id)
        }
    }, [folderId, accessScope, selectedFolder])

    useEffect(() => {
        if (accessScope === 'department') {
            setDepartmentId(userDepartmentId)
        }
        if (accessScope === 'personal') {
            setDepartmentId('')
        }
    }, [accessScope, userDepartmentId])

    const fileInputRef = useRef<HTMLInputElement | null>(null)

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const selectedFile = e.target.files[0]
            if (validateFile(selectedFile)) {
                setFile(selectedFile)
                setError(null)
            }
        }
    }

    /**
     * ✅ NEW: Validate scope/folder/department compatibility
     * Rules (from backend):
     * 1. Personal folder → document MUST be personal scope
     * 2. Department folder → document cannot be company scope
     * 3. Company folder → document can be any scope
     * 4. Department scope → requires effective department_id
     * 
     * Reference: backend/services/document_upload_service.py lines 253-297
     */
    const validateUploadRules = (): boolean => {
        // Rule 2-4: Validate scope compatibility with folder
        if (folderId) {
            if (!selectedFolder) {
                setError('❌ Folder không tồn tại')
                return false
            }

            // Personal folder → document MUST be personal
            if (selectedFolder.access_scope === 'personal' && accessScope !== 'personal') {
                setError('❌ Tài liệu trong personal folder phải có access_scope="personal", không được "' + accessScope + '"')
                return false
            }

            // Department folder → document cannot be company-wide
            // (but can be department or personal - will inherit in backend)
            if (selectedFolder.access_scope === 'department' && accessScope === 'company') {
                setError('❌ Tài liệu trong department folder không thể là company-wide')
                return false
            }
        }

        // Rule: department scope requires effective department_id
        const effectiveDepartmentId =
            accessScope === 'department'
                ? (selectedFolder?.access_scope === 'department'
                    ? selectedFolder.department_id
                    : departmentId)
                : ''

        if (accessScope === 'department' && !effectiveDepartmentId) {
            setError('⚠️ Vui lòng chọn phòng ban cho tài liệu department-scoped')
            return false
        }

        return true
    }

    const handleUpload = async () => {
        if (!file) {
            setError('Vui lòng chọn một file.')
            console.log('❌ Upload blocked: No file selected')
            return
        }

        if (!validateFile(file)) {
            console.log('❌ Upload blocked: File validation failed')
            return
        }

        // ✅ NEW: Validate scope/folder/department before uploading
        if (!validateUploadRules()) {
            console.log('❌ Upload blocked: Upload rules validation failed')
            return  // Stop upload, show error message
        }

        console.log('📤 Starting upload:', {
            fileName: file.name,
            fileSize: file.size,
            accessScope,
            folderId: folderId || 'none',
            departmentId: departmentId || 'none',
        })

        setIsUploading(true)
        setError(null)

        try {
            const tagsArray = tagsInput.split(',').map(t => t.trim()).filter(t => t !== '')
            const effectiveDepartmentId =
                accessScope === 'department'
                    ? (selectedFolder?.access_scope === 'department'
                        ? selectedFolder.department_id || undefined
                        : departmentId || undefined)
                    : undefined

            console.log('📋 Upload config:', {
                file: file.name,
                folderId: folderId || undefined,
                departmentId: effectiveDepartmentId,
                accessScope,
                tagsArray,
                description: description || undefined,
            })

            await uploadService.uploadFile(file, {
                folderId: folderId || undefined,
                departmentId: effectiveDepartmentId,
                accessScope,
                description: description || undefined,
                tags: tagsArray,
                onProgress: (prog) => {
                    console.log(`📈 Upload progress: ${prog.percentage}%`)
                    setProgress(prog.percentage)
                }
            })

            console.log('✅ Upload successful!')
            if (onSuccess) onSuccess()
            onClose()
        } catch (err: any) {
            const errorMsg = err.message || 'Upload thất bại.'
            console.error('❌ Upload failed:', err)
            setError(errorMsg)
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
                                ref={fileInputRef}
                                onChange={handleFileChange}
                                disabled={isUploading}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed z-10"
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
                        {allowedScopes.length === 1 ? (
                            <div className="px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-sm text-slate-700">
                                {allowedScopes[0] === 'company' && 'Toàn công ty'}
                                {allowedScopes[0] === 'department' && 'Phòng ban'}
                                {allowedScopes[0] === 'personal' && 'Cá nhân'}
                            </div>
                        ) : (
                            <select
                                value={accessScope}
                                onChange={(e) => setAccessScope(e.target.value as any)}
                                disabled={isUploading || allowedScopes.length <= 1}
                                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300] transition-colors disabled:opacity-75 disabled:bg-slate-100"
                            >
                                {allowedScopes.includes('company') && <option value="company">Toàn công ty</option>}
                                {allowedScopes.includes('department') && <option value="department">Phòng ban</option>}
                                {allowedScopes.includes('personal') && <option value="personal">Cá nhân</option>}
                            </select>
                        )}

                        {/* ✅ NEW: Helper text explaining scope options */}
                        <p className="text-xs text-slate-600 mt-2">
                            {accessScope === 'company' && '🏢 Mọi người trong công ty có thể xem tài liệu này'}
                            {accessScope === 'department' && '👥 Chỉ những người trong phòng ban được chọn có thể xem'}
                            {accessScope === 'personal' && '🔒 Chỉ bạn có thể xem tài liệu này'}
                        </p>
                    </div>

                    {/* Department */}
                    {accessScope === 'department' && (
                        <div className="bg-amber-50 p-4 rounded-xl border-l-4 border-amber-400">
                            <label className="block text-sm font-bold text-amber-900 mb-2">
                                Phòng ban <span className="text-red-500">*</span> (Chỉ phòng ban của bạn)
                            </label>
                            <select
                                value={departmentId}
                                onChange={(e) => setDepartmentId(e.target.value)}
                                disabled={isUploading || !!userDepartmentId}
                                className={`w-full px-4 py-2.5 bg-white border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300] transition-colors ${!departmentId ? 'border-red-500 border-2' : 'border-amber-300'}`}
                            >
                                {userDepartmentId ? (
                                    <>
                                        <option value="">-- Phòng ban của bạn --</option>
                                        {departments
                                            .filter((dept) => dept.id === userDepartmentId)
                                            .map((dept) => (
                                                <option key={dept.id} value={dept.id}>
                                                    {dept.name}
                                                </option>
                                            ))}
                                    </>
                                ) : (
                                    <>
                                        <option value="">-- Chọn phòng ban --</option>
                                        {departments.map((dept, index) => (
                                            <option key={`${dept.id}-${index}`} value={dept.id}>{dept.name}</option>
                                        ))}
                                    </>
                                )}
                            </select>
                            <p className="text-xs text-amber-700 mt-2">
                                {selectedFolder?.access_scope === 'department'
                                    ? '👥 Department folder sẽ tự động kế thừa phòng ban từ thư mục'
                                    : '👥 Chỉ phòng ban của bạn mới được chọn và lưu tài liệu'}
                            </p>
                        </div>
                    )}

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

                        {/* ✅ NEW: Show warning if folder scope differs from selected scope */}
                        {folderId && selectedFolder?.access_scope && (
                            <p className="text-xs text-blue-700 mt-2">
                                ℹ️ Thư mục đang chọn có phạm vi: {selectedFolder.access_scope === 'company' ? '🏢 công ty' : selectedFolder.access_scope === 'department' ? '👥 phòng ban' : '🔒 cá nhân'}
                            </p>
                        )}
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
                        disabled={!file || isUploading}
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
