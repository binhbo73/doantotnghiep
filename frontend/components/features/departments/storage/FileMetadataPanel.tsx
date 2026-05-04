/**
 * File Metadata Panel Component
 * Displays details about selected folder or file in right sidebar
 */

'use client';

import React from 'react';
import {
    Download,
    Share2,
    Clock,
    User,
    HardDrive,
    Eye,
    MoreVertical,
    FileText,
    Archive,
} from 'lucide-react';
import { FolderTreeNode, DocumentNode } from '@/hooks/departments/useDepartmentFolders';

interface FileMetadataPanelProps {
    selectedFolder?: FolderTreeNode | null;
    selectedDocument?: DocumentNode | null;
    onDownload?: () => void;
    onShare?: () => void;
}

function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
    });
}

function getFilePreviewColor(fileType: string): string {
    const type = fileType.toLowerCase();
    if (type.includes('pdf')) return 'bg-red-50 text-red-600';
    if (type.includes('doc') || type.includes('word')) return 'bg-blue-50 text-blue-600';
    if (type.includes('xls') || type.includes('excel') || type.includes('sheet')) return 'bg-green-50 text-green-600';
    if (type.includes('ppt') || type.includes('powerpoint') || type.includes('presentation')) return 'bg-orange-50 text-orange-600';
    if (type.includes('zip') || type.includes('rar') || type.includes('tar') || type.includes('gz')) return 'bg-amber-50 text-amber-600';
    if (type.includes('png') || type.includes('jpg') || type.includes('jpeg') || type.includes('gif') || type.includes('svg') || type.includes('webp')) return 'bg-purple-50 text-purple-600';
    if (type.includes('mp4') || type.includes('avi') || type.includes('mov') || type.includes('video')) return 'bg-pink-50 text-pink-600';
    if (type.includes('txt') || type.includes('text')) return 'bg-slate-100 text-slate-600';
    if (type.includes('md') || type.includes('markdown')) return 'bg-indigo-50 text-indigo-600';
    if (type.includes('json') || type.includes('xml') || type.includes('yaml') || type.includes('yml')) return 'bg-teal-50 text-teal-600';
    return 'bg-slate-100 text-slate-500';
}

export function FileMetadataPanel({
    selectedFolder,
    selectedDocument,
    onDownload,
    onShare,
}: FileMetadataPanelProps) {
    const item = selectedDocument || selectedFolder;

    if (!item) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <Eye className="w-12 h-12 text-gray-300 mb-3" />
                <p className="text-sm text-gray-400">
                    Chọn một thư mục hoặc tệp để xem chi tiết
                </p>
            </div>
        );
    }

    const isDocument = selectedDocument !== null;
    const isFolder = selectedFolder !== null;

    return (
        <div className="h-full overflow-y-auto flex flex-col gap-6">
            {/* Preview Section */}
            <div>
                {isDocument ? (
                    <div className={`rounded-xl p-6 flex items-center justify-center min-h-40 ${getFilePreviewColor(selectedDocument!.file_type)}`}>
                        <div className="text-center">
                            {selectedDocument!.file_type.toLowerCase() === 'zip' ? (
                                <Archive className="w-16 h-16 mx-auto opacity-80" />
                            ) : (
                                <FileText className="w-16 h-16 mx-auto opacity-80" />
                            )}
                            <div className="text-xs font-bold mt-3 uppercase">
                                {selectedDocument!.file_type}
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="rounded-xl p-6 flex items-center justify-center min-h-40 bg-slate-50">
                        <div className="text-center">
                            <div className="text-5xl mb-2">📁</div>
                            <p className="text-xs text-gray-600 font-semibold">
                                Thư mục
                            </p>
                        </div>
                    </div>
                )}
            </div>

            {/* Item Details */}
            <div className="space-y-2">
                <h3 className="text-base font-bold text-gray-900 truncate">
                    {isDocument
                        ? selectedDocument!.original_name || selectedDocument!.filename
                        : selectedFolder!.name}
                </h3>
                <p className="text-xs text-gray-500">
                    {isDocument
                        ? `${selectedDocument!.file_type} • ${formatFileSize(
                            selectedDocument!.file_size || 0
                        )}`
                        : `Thư mục • ${selectedFolder!.documents.length +
                        selectedFolder!.subFolders.length
                        } mục`}
                </p>
            </div>

            {/* Action Buttons */}
            <div className="grid grid-cols-2 gap-2">
                <button
                    onClick={onDownload}
                    className="flex items-center justify-center gap-2 px-3 py-2.5 bg-gradient-to-r from-[#9d4300] to-[#f97316] text-white rounded-lg hover:opacity-90 transition-all text-sm font-medium shadow-sm"
                >
                    <Download className="w-4 h-4" />
                    <span>Tải về</span>
                </button>
                <button
                    onClick={onShare}
                    className="flex items-center justify-center gap-2 px-3 py-2.5 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-all text-sm font-medium"
                >
                    <Share2 className="w-4 h-4" />
                    <span>Chia sẻ</span>
                </button>
            </div>

            {/* Metadata Section */}
            <div className="space-y-4 pt-4 border-t border-gray-200">
                <h4 className="text-xs font-bold uppercase tracking-widest text-gray-500">
                    Chi tiết tài liệu
                </h4>

                <div className="space-y-4 text-sm">
                    {/* File Size (Documents) */}
                    {isDocument && (
                        <div className="flex items-center gap-3">
                            <HardDrive className="w-4 h-4 text-gray-400 flex-shrink-0" />
                            <div className="flex-1">
                                <p className="text-xs text-gray-500">Kích thước</p>
                                <p className="text-sm text-gray-900 font-medium">
                                    {formatFileSize(
                                        selectedDocument!.file_size || 0
                                    )}
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Created Date */}
                    <div className="flex items-center gap-3">
                        <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
                        <div className="flex-1">
                            <p className="text-xs text-gray-500">Ngày tạo</p>
                            <p className="text-sm text-gray-900 font-medium">
                                {formatDate(item.created_at)}
                            </p>
                        </div>
                    </div>

                    {/* Last Modified */}
                    <div className="flex items-center gap-3">
                        <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
                        <div className="flex-1">
                            <p className="text-xs text-gray-500">Cập nhật lần cuối</p>
                            <p className="text-sm text-gray-900 font-medium">
                                {formatDate(item.updated_at)}
                            </p>
                        </div>
                    </div>

                    {/* Access Scope */}
                    <div className="flex items-center gap-3">
                        <Eye className="w-4 h-4 text-gray-400 flex-shrink-0" />
                        <div className="flex-1">
                            <p className="text-xs text-gray-500">Phạm vi truy cập</p>
                            <p className="text-sm text-gray-900 font-medium">
                                {item.access_scope === 'PUBLIC'
                                    ? 'Công khai'
                                    : 'Riêng tư'}
                            </p>
                        </div>
                    </div>

                    {/* Status (Documents only) */}
                    {isDocument && selectedDocument!.status && !['processing', 'pending'].includes(selectedDocument!.status) && (
                        <div className="flex items-center gap-3">
                            <div className="w-4 h-4 rounded-full flex-shrink-0 bg-green-500" />
                            <div className="flex-1">
                                <p className="text-xs text-gray-500">Trạng thái</p>
                                <p className="text-sm text-gray-900 font-medium capitalize">
                                    {selectedDocument!.status === 'completed'
                                        ? 'Hoàn thành'
                                        : selectedDocument!.status === 'failed'
                                            ? 'Lỗi'
                                            : selectedDocument!.status}
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Uploader Info (Documents only) */}
                    {isDocument && selectedDocument!.uploader && (
                        <div className="flex items-center gap-3">
                            <User className="w-4 h-4 text-gray-400 flex-shrink-0" />
                            <div className="flex-1">
                                <p className="text-xs text-gray-500">Người tải lên</p>
                                <p className="text-sm text-gray-900 font-medium">
                                    {selectedDocument!.uploader.full_name ||
                                        selectedDocument!.uploader.username ||
                                        'Không xác định'}
                                </p>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* More Options */}
            <button className="flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-200 rounded-lg hover:bg-gray-50 transition-all text-sm text-gray-600 font-medium mt-auto">
                <MoreVertical className="w-4 h-4" />
                <span>Thêm tùy chọn</span>
            </button>
        </div>
    );
}
