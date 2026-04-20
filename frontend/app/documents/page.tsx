/**
 * Example: Documents Page Component
 * Demonstrates the complete flow from component → hooks → services → API
 */

'use client'

import { useState } from 'react'
import { useDocuments, useDeleteDocument, useUploadDocuments } from '@/hooks/useDocument'
import { ErrorBoundary } from '@/components/error/ErrorBoundary'
import { logger } from '@/services/logger'
import { Loader2, Trash2, Upload, AlertCircle, Search } from 'lucide-react'
import type { Document } from '@/types/api'

interface DocumentsPageProps {
    initialLimit?: number
}

export default function DocumentsPage({ initialLimit = 20 }: DocumentsPageProps) {
    const [page, setPage] = useState(1)
    const [searchTerm, setSearchTerm] = useState('')
    const [fileStatus, setFileStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')
    const [uploadProgress, setUploadProgress] = useState(0)

    // Server state management with React Query
    const { data: response, isLoading, error, refetch } = useDocuments({
        limit: initialLimit,
        offset: (page - 1) * initialLimit,
        search: searchTerm || undefined,
    })

    // Mutations
    const deleteDocument = useDeleteDocument()
    const uploadDocuments = useUploadDocuments()

    // Handle file upload
    const handleUpload = async (files: FileList) => {
        if (files.length === 0) return

        setFileStatus('uploading')
        setUploadProgress(0)

        try {
            const fileArray = Array.from(files)
            logger.info('Starting upload', { count: fileArray.length })

            await uploadDocuments.mutateAsync(fileArray, {
                onSuccess: () => {
                    setFileStatus('success')
                    setUploadProgress(100)
                    setTimeout(() => setFileStatus('idle'), 2000)
                },
            })
        } catch (err) {
            setFileStatus('error')
            logger.error('Upload failed', err)
        }
    }

    // Handle delete
    const handleDelete = (documentId: string) => {
        if (window.confirm('Are you sure you want to delete this document?')) {
            deleteDocument.mutate(documentId)
        }
    }

    return (
        <ErrorBoundary>
            <div className="min-h-screen bg-gray-50">
                {/* Header */}
                <div className="bg-white border-b">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                        <h1 className="text-3xl font-bold text-gray-900">Documents</h1>
                        <p className="mt-2 text-gray-600">Manage your documents and files</p>
                    </div>
                </div>

                {/* Main Content */}
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    {/* Upload Section */}
                    <div className="bg-white rounded-lg shadow mb-8 p-6">
                        <label className="flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-lg p-12 cursor-pointer hover:border-blue-500 transition-colors">
                            <Upload className="h-12 w-12 text-gray-400 mb-2" />
                            <span className="text-lg font-medium text-gray-900">
                                {fileStatus === 'uploading' ? `Uploading: ${uploadProgress}%` : 'Click to upload files'}
                            </span>
                            <span className="text-sm text-gray-500 mt-1">or drag and drop</span>

                            {fileStatus === 'success' && (
                                <span className="text-green-600 text-sm mt-2">✓ Upload successful!</span>
                            )}
                            {fileStatus === 'error' && (
                                <span className="text-red-600 text-sm mt-2">✗ Upload failed</span>
                            )}

                            <input
                                type="file"
                                multiple
                                onChange={(e) => handleUpload(e.currentTarget.files!)}
                                disabled={fileStatus === 'uploading'}
                                className="hidden"
                            />
                        </label>
                    </div>

                    {/* Search Section */}
                    <div className="mb-6 flex gap-2">
                        <div className="flex-1 relative">
                            <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                            <input
                                type="text"
                                placeholder="Search documents..."
                                value={searchTerm}
                                onChange={(e) => {
                                    setSearchTerm(e.target.value)
                                    setPage(1) // Reset to first page on search
                                }}
                                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>
                        <button
                            onClick={() => refetch()}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            Refresh
                        </button>
                    </div>

                    {/* Error State */}
                    {error && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex gap-3">
                            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                            <div>
                                <h3 className="font-medium text-red-900">Error loading documents</h3>
                                <p className="text-sm text-red-700 mt-1">{error.message}</p>
                                <button
                                    onClick={() => refetch()}
                                    className="text-sm text-red-700 hover:text-red-900 font-medium mt-2 underline"
                                >
                                    Try again
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Loading State */}
                    {isLoading && (
                        <div className="flex justify-center items-center h-64">
                            <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
                        </div>
                    )}

                    {/* Empty State */}
                    {response?.items.length === 0 && !isLoading && (
                        <div className="text-center py-12">
                            <h3 className="text-lg font-medium text-gray-900">No documents found</h3>
                            <p className="text-gray-600 mt-1">Get started by uploading your first document</p>
                        </div>
                    )}

                    {/* Documents Grid */}
                    {response && response.items.length > 0 && (
                        <>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                                {response.items.map((doc: Document) => (
                                    <div
                                        key={doc.id}
                                        className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow overflow-hidden group"
                                    >
                                        <div className="p-4">
                                            {/* Document Info */}
                                            <div className="flex items-start justify-between mb-2">
                                                <div className="flex-1">
                                                    <h3 className="font-medium text-gray-900 truncate">
                                                        {doc.original_name}
                                                    </h3>
                                                    <p className="text-xs text-gray-500 mt-1">
                                                        {(doc.file_size / 1024 / 1024).toFixed(2)} MB
                                                    </p>
                                                </div>
                                                <span className="inline-block px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                                                    {doc.file_type.toUpperCase()}
                                                </span>
                                            </div>

                                            {/* Status */}
                                            <div className="flex items-center gap-2 mt-2">
                                                <span
                                                    className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${doc.status === 'completed'
                                                            ? 'bg-green-100 text-green-800'
                                                            : doc.status === 'processing'
                                                                ? 'bg-yellow-100 text-yellow-800'
                                                                : doc.status === 'failed'
                                                                    ? 'bg-red-100 text-red-800'
                                                                    : 'bg-gray-100 text-gray-800'
                                                        }`}
                                                >
                                                    {doc.status}
                                                </span>
                                            </div>

                                            {/* Metadata */}
                                            <div className="mt-3 pt-3 border-t border-gray-200 space-y-1">
                                                <p className="text-xs text-gray-500">
                                                    Uploaded: {new Date(doc.created_at).toLocaleDateString()}
                                                </p>
                                                <p className="text-xs text-gray-500">
                                                    Language: {doc.doc_language.toUpperCase()}
                                                </p>
                                            </div>

                                            {/* Actions */}
                                            <div className="mt-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button
                                                    onClick={() => handleDelete(doc.id)}
                                                    disabled={deleteDocument.isPending}
                                                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-red-50 text-red-700 rounded hover:bg-red-100 transition-colors disabled:opacity-50"
                                                >
                                                    {deleteDocument.isPending ? (
                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <Trash2 className="h-4 w-4" />
                                                    )}
                                                    Delete
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Pagination */}
                            {response.pages > 1 && (
                                <div className="flex justify-center gap-2 mt-8">
                                    {Array.from({ length: response.pages }, (_, i) => i + 1).map((p) => (
                                        <button
                                            key={p}
                                            onClick={() => setPage(p)}
                                            className={`px-4 py-2 rounded-lg transition-colors ${p === page
                                                    ? 'bg-blue-600 text-white'
                                                    : 'bg-white text-gray-900 border border-gray-300 hover:border-blue-500'
                                                }`}
                                        >
                                            {p}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </ErrorBoundary>
    )
}
