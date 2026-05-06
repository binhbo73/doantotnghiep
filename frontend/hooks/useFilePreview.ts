'use client'

/**
 * useFilePreview Hook
 * Provides file preview functionality for different file types
 */

import { useState, useEffect } from 'react'
import { logger } from '@/services/logger'

interface FilePreview {
    url: string | null
    type: 'image' | 'pdf' | 'text' | 'unsupported'
    loading: boolean
    error: string | null
}

interface UseFilePreviewOptions {
    maxSize?: number // Max file size in MB for preview
    supportedTypes?: string[]
}

export function useFilePreview(file: File | null, options: UseFilePreviewOptions = {}) {
    const [preview, setPreview] = useState<FilePreview>({
        url: null,
        type: 'unsupported',
        loading: false,
        error: null,
    })

    const {
        maxSize = 10, // 10MB default
        supportedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf', 'text/plain']
    } = options

    useEffect(() => {
        if (!file) {
            setPreview({
                url: null,
                type: 'unsupported',
                loading: false,
                error: null,
            })
            return
        }

        // Check file size
        const fileSizeMB = file.size / (1024 * 1024)
        if (fileSizeMB > maxSize) {
            setPreview({
                url: null,
                type: 'unsupported',
                loading: false,
                error: `File size too large (${fileSizeMB.toFixed(1)}MB). Max allowed: ${maxSize}MB`,
            })
            return
        }

        // Check file type
        if (!supportedTypes.includes(file.type)) {
            setPreview({
                url: null,
                type: 'unsupported',
                loading: false,
                error: `Unsupported file type: ${file.type}`,
            })
            return
        }

        setPreview(prev => ({ ...prev, loading: true, error: null }))

        try {
            // Create object URL for preview
            const objectUrl = URL.createObjectURL(file)

            let type: FilePreview['type'] = 'unsupported'
            if (file.type.startsWith('image/')) {
                type = 'image'
            } else if (file.type === 'application/pdf') {
                type = 'pdf'
            } else if (file.type === 'text/plain') {
                type = 'text'
            }

            setPreview({
                url: objectUrl,
                type,
                loading: false,
                error: null,
            })

            logger.debug('File preview generated', { fileName: file.name, type, size: fileSizeMB.toFixed(2) + 'MB' })

        } catch (error) {
            logger.error('Failed to generate file preview', { error, fileName: file.name })
            setPreview({
                url: null,
                type: 'unsupported',
                loading: false,
                error: 'Failed to generate preview',
            })
        }

        // Cleanup function
        return () => {
            if (preview.url && preview.url.startsWith('blob:')) {
                URL.revokeObjectURL(preview.url)
            }
        }
    }, [file, maxSize, supportedTypes])

    return preview
}

/**
 * File Preview Component
 */
interface FilePreviewComponentProps {
    preview: FilePreview
    className?: string
}

export function FilePreviewComponent({ preview, className = '' }: FilePreviewComponentProps) {
    if (preview.loading) {
        return (
            <div className= {`flex items-center justify-center bg-gray-100 rounded-lg ${className}`
    }>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" > </div>
            </div>
        )
}

if (preview.error) {
    return (
        <div className= {`flex items-center justify-center bg-red-50 border border-red-200 rounded-lg p-4 ${className}`
}>
    <div className="text-center" >
        <div className="text-red-500 text-sm mb-2" >⚠️ Preview Error </div>
            < div className = "text-red-400 text-xs" > { preview.error } </div>
                </div>
                </div>
        )
    }

if (!preview.url) {
    return (
        <div className= {`flex items-center justify-center bg-gray-100 rounded-lg ${className}`
}>
    <div className="text-gray-500 text-sm" > No preview available </div>
        </div>
        )
    }

switch (preview.type) {
    case 'image':
        return (
            <img
                    src= { preview.url }
        alt = "File preview"
        className = {`max-w-full max-h-full object-contain rounded-lg ${className}`
}
                />
            )

        case 'pdf':
return (
    <iframe
                    src= { preview.url }
className = {`w-full h-full rounded-lg ${className}`}
title = "PDF Preview"
    />
            )

        case 'text':
return (
    <div className= {`bg-gray-50 p-4 rounded-lg overflow-auto max-h-96 ${className}`}>
        <pre className="text-sm text-gray-800 whitespace-pre-wrap" >
            {/* Note: In real implementation, you'd fetch and display text content */ }
                        Text file preview would be shown here
    </pre>
    </div>
            )

        default:
return (
    <div className= {`flex items-center justify-center bg-gray-100 rounded-lg ${className}`}>
        <div className="text-center" >
            <div className="text-gray-500 text-sm mb-2" >📄</div>
                < div className = "text-gray-400 text-xs" > Preview not supported </div>
                    </div>
                    </div>
            )
    }
}