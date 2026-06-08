/**
 * Upload Service - Centralized file upload with progress tracking
 */

import { ApiError } from '@/services/api/errors'
import { logger } from '@/services/logger'
import { buildDirectApiUrl } from '@/config/api'
import { getAuthToken } from '@/services/auth'
import type { Document } from '@/types/api'

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
    folderId?: string
    departmentId?: string
    accessScope?: string
    description?: string
    tags?: string[]
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
    if (options?.folderId) formData.append('folder_id', options.folderId)
    if (options?.departmentId) formData.append('department_id', options.departmentId)
    if (options?.accessScope) formData.append('access_scope', options.accessScope)
    if (options?.description) formData.append('description', options.description)
    if (options?.tags && options.tags.length > 0) formData.append('tags', options.tags.join(','))

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
            logger.debug(`XHR Load: status=${xhr.status}`)

            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = JSON.parse(xhr.responseText)
                    const document = response.data || response
                    logger.info('File uploaded successfully', { filename: file.name })

                    // Dispatch real-time notification event
                    window.dispatchEvent(new CustomEvent('upload:complete', {
                        detail: { fileName: file.name, document }
                    }))

                    resolve(document)
                } catch (err) {
                    logger.error('Response parse error during upload', { error: err })
                    reject(new Error('Invalid response from server'))
                }
            } else {
                logger.warn(`Upload failed with status ${xhr.status}`, { filename: file.name })
                try {
                    const error = JSON.parse(xhr.responseText)
                    const apiError = new ApiError(
                        xhr.status,
                        error.message || `Upload failed with status ${xhr.status}`
                    )

                    // Dispatch real-time notification event
                    window.dispatchEvent(new CustomEvent('upload:failed', {
                        detail: { fileName: file.name, error: apiError.message }
                    }))

                    reject(apiError)
                } catch {
                    const apiError = new ApiError(xhr.status, `Upload failed with status ${xhr.status}`)

                    // Dispatch real-time notification event
                    window.dispatchEvent(new CustomEvent('upload:failed', {
                        detail: { fileName: file.name, error: apiError.message }
                    }))

                    reject(apiError)
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

        // Open first, then set headers, then send
        xhr.open('POST', buildDirectApiUrl('/documents/upload'))
        xhr.withCredentials = true

        // Fallback auth header only if a token is available in legacy setups
        const token = getAuthToken()
        if (token) {
            xhr.setRequestHeader('Authorization', `Bearer ${token}`)
        }

        xhr.send(formData)
    })
}

export async function uploadDocumentVersion(
    documentId: string,
    file: File,
    options?: {
        versionLock?: number
        changeSummary?: string
        updateMode?: 'auto' | 'full' | 'amendment'
        onProgress?: (progress: UploadProgress) => void
        timeout?: number
    }
): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)
    if (options?.versionLock) formData.append('version_lock', String(options.versionLock))
    if (options?.changeSummary) formData.append('change_summary', options.changeSummary)
    formData.append('update_mode', options?.updateMode || 'auto')

    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest()
        if (options?.onProgress) {
            xhr.upload.addEventListener('progress', (event) => {
                if (!event.lengthComputable) return
                options.onProgress?.({
                    loaded: event.loaded,
                    total: event.total,
                    percentage: Math.round((event.loaded / event.total) * 100),
                })
            })
        }
        xhr.addEventListener('load', () => {
            let response: unknown = null
            try {
                response = JSON.parse(xhr.responseText)
            } catch {
                response = null
            }
            const responseRecord = response && typeof response === 'object'
                ? response as Record<string, unknown>
                : null
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve((responseRecord?.data || response) as Document)
                return
            }
            reject(new ApiError(
                xhr.status,
                String(
                    responseRecord?.message
                    || responseRecord?.error
                    || `Version upload failed with status ${xhr.status}`
                ),
            ))
        })
        xhr.addEventListener('error', () => reject(new Error('Version upload failed')))
        xhr.addEventListener('timeout', () => reject(new Error('Version upload timeout')))
        xhr.timeout = options?.timeout || 120000
        xhr.open('POST', buildDirectApiUrl(`/documents/${documentId}/versions`))
        xhr.withCredentials = true
        const token = getAuthToken()
        if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
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
    uploadDocumentVersion,
    uploadMultipleFiles,
    resumeUpload,
}
