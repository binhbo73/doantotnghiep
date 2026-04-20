/**
 * Upload Service - Centralized file upload with progress tracking
 */

import { api } from '@/services/api/client'
import { ApiError } from '@/services/api/errors'
import { logger } from '@/services/logger'
import type { Document, UploadDocumentRequest } from '@/types/api'

interface UploadProgress {
    loaded: number
    total: number
    percentage: number
}

interface UploadOptions {
    onProgress?: (progress: UploadProgress) => void
    onSuccess?: (document: Document) => void
    onError?: (error: Error) => void
    maxRetries?: number
    timeout?: number
}

/**
 * Upload a single file
 */
export async function uploadFile(
    file: File,
    options?: Omit<UploadOptions, 'onSuccess' | 'onError'>
): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)

    // Use XMLHttpRequest for progress tracking (fetch doesn't support upload progress)
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest()

        // Track upload progress
        if (options?.onProgress) {
            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable) {
                    const percentage = Math.round((event.loaded / event.total) * 100)
                    options.onProgress?.({
                        loaded: event.loaded,
                        total: event.total,
                        percentage,
                    })
                }
            })
        }

        // Handle completion
        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = JSON.parse(xhr.responseText)
                    const document = response.data || response
                    logger.info('File uploaded successfully', { filename: file.name })
                    resolve(document)
                } catch (err) {
                    reject(new Error('Invalid response from server'))
                }
            } else {
                try {
                    const error = JSON.parse(xhr.responseText)
                    reject(
                        new ApiError(
                            xhr.status,
                            error.message || `Upload failed with status ${xhr.status}`
                        )
                    )
                } catch {
                    reject(new ApiError(xhr.status, `Upload failed with status ${xhr.status}`))
                }
            }
        })

        // Handle error
        xhr.addEventListener('error', () => {
            reject(new Error('Upload failed'))
        })

        // Handle timeout
        xhr.addEventListener('timeout', () => {
            reject(new Error('Upload timeout'))
        })

        // Set timeout
        xhr.timeout = options?.timeout || 120000 // 2 minutes

        // Set auth header
        const token = localStorage.getItem('auth_token')
        if (token) {
            xhr.setRequestHeader('Authorization', `Bearer ${token}`)
        }

        // Open and send
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
        xhr.open('POST', `${baseUrl}/documents/upload`)
        xhr.send(formData)
    })
}

/**
 * Upload multiple files
 */
export async function uploadMultipleFiles(
    files: File[],
    options?: UploadOptions
): Promise<Document[]> {
    const results: Document[] = []
    const errors: Array<{ file: string; error: Error }> = []

    for (let i = 0; i < files.length; i++) {
        const file = files[i]

        try {
            logger.info(`Uploading file ${i + 1}/${files.length}`, { filename: file.name })

            const document = await uploadFile(file, {
                ...options,
                onProgress: (progress) => {
                    // Adjust progress to show overall progress across all files
                    const totalProgress = ((i + progress.percentage / 100) / files.length) * 100
                    options?.onProgress?.({
                        loaded: progress.loaded,
                        total: progress.total,
                        percentage: Math.round(totalProgress),
                    })
                },
            })

            results.push(document)
            options?.onSuccess?.(document)
        } catch (error) {
            const err = error instanceof Error ? error : new Error(String(error))
            errors.push({ file: file.name, error: err })
            options?.onError?.(err)
        }
    }

    // Log summary
    logger.info('Upload batch complete', {
        total: files.length,
        successful: results.length,
        failed: errors.length,
    })

    // Throw if all failed
    if (results.length === 0 && errors.length > 0) {
        throw new Error(`All ${errors.length} files failed to upload`)
    }

    return results
}

/**
 * Resume interrupted upload (simple retry)
 */
export async function resumeUpload(
    file: File,
    options?: UploadOptions
): Promise<Document> {
    let lastError: Error | null = null
    const maxRetries = options?.maxRetries || 3

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            logger.info(`Upload attempt ${attempt}/${maxRetries}`, { filename: file.name })
            return await uploadFile(file, options)
        } catch (error) {
            lastError = error instanceof Error ? error : new Error(String(error))
            logger.warn(`Upload attempt ${attempt} failed`, {
                filename: file.name,
                error: lastError.message,
            })

            // Wait before retry
            if (attempt < maxRetries) {
                await new Promise((resolve) => setTimeout(resolve, 1000 * attempt))
            }
        }
    }

    throw lastError || new Error('Upload failed after multiple attempts')
}

export const uploadService = {
    uploadFile,
    uploadMultipleFiles,
    resumeUpload,
}
