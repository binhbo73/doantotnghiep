/**
 * Department Storage Archive Tab Component
 * Main container for browsing department documents and folders
 */

'use client';

import React, { useState } from 'react';
import { Search, Loader2, AlertCircle } from 'lucide-react';
import { useDepartmentFolders } from '@/hooks/departments/useDepartmentFolders';
import { FolderTree } from './FolderTree';
import { FileMetadataPanel } from './FileMetadataPanel';

interface DepartmentStorageArchiveProps {
    departmentId: string;
    departmentName: string;
}

export function DepartmentStorageArchive({
    departmentId,
    departmentName,
}: DepartmentStorageArchiveProps) {
    const {
        folders,
        loading,
        error,
        selectedFolder,
        selectedDocument,
        selectFolder,
        selectDocument,
        toggleFolder,
        refresh,
    } = useDepartmentFolders(departmentId);

    const [searchQuery, setSearchQuery] = useState('');

    const handleDownload = () => {
        if (selectedDocument) {
            // TODO: Implement download logic
            alert(`Tải về: ${selectedDocument.original_name || selectedDocument.filename}`);
        }
    };

    const handleShare = () => {
        if (selectedDocument || selectedFolder) {
            // TODO: Implement share logic
            alert('Chức năng chia sẻ đang được phát triển');
        }
    };

    if (error && !folders.length) {
        return (
            <div className="space-y-6">
                {/* Header */}
                <div>
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-gray-500 mb-3">
                        <span>Phòng ban</span>
                        <span className="text-gray-300">›</span>
                        <span className="text-blue-600">Kho lưu trữ</span>
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 mb-2">
                            Kho lưu trữ: {departmentName}
                        </h1>
                        <p className="text-sm text-gray-500">
                            Quản lý và truy cập kiến thức tập trung của{' '}
                            {departmentName}
                        </p>
                    </div>
                </div>

                {/* Error State */}
                <div className="bg-white rounded-xl border border-red-200 p-8">
                    <div className="flex items-center gap-4 text-center">
                        <AlertCircle className="w-12 h-12 text-red-500 flex-shrink-0" />
                        <div className="flex-1">
                            <p className="text-red-600 font-semibold mb-2">Lỗi tải dữ liệu</p>
                            <p className="text-sm text-gray-500 mb-4">{error}</p>
                            <button
                                onClick={refresh}
                                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-all text-sm font-medium"
                            >
                                Thử lại
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-gray-500 mb-3">
                    <span>Phòng ban</span>
                    <span className="text-gray-300">›</span>
                    <span className="text-blue-600">Kho lưu trữ</span>
                </div>
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">
                        Kho lưu trữ: {departmentName}
                    </h1>
                    <p className="text-sm text-gray-500">
                        Quản lý và truy cập kiến thức tập trung của{' '}
                        {departmentName}
                    </p>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Left Panel: Folder Tree */}
                <div className="lg:col-span-2 space-y-4">
                    {/* Search Input */}
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Tìm kiếm thư mục hoặc tệp..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        />
                    </div>

                    {/* Folder Tree Container */}
                    <div className="bg-white rounded-xl border border-gray-200 p-6 min-h-96">
                        {loading ? (
                            <div className="flex items-center justify-center h-96">
                                <div className="text-center">
                                    <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-2" />
                                    <p className="text-sm text-gray-500">
                                        Đang tải dữ liệu...
                                    </p>
                                </div>
                            </div>
                        ) : folders.length > 0 ? (
                            <FolderTree
                                folders={folders}
                                selectedFolder={selectedFolder}
                                selectedDocument={selectedDocument}
                                onSelectFolder={selectFolder}
                                onSelectDocument={selectDocument}
                                onToggleFolder={toggleFolder}
                            />
                        ) : (
                            <div className="flex items-center justify-center h-96 text-center">
                                <div>
                                    <p className="text-gray-500 mb-3">Không có thư mục nào</p>
                                    <button
                                        onClick={refresh}
                                        className="text-xs text-blue-600 hover:underline"
                                    >
                                        Tải lại dữ liệu
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Keyboard Shortcuts */}
                    <div className="flex items-center gap-4 text-xs text-gray-400 px-2">
                        <div className="flex items-center gap-2">
                            <kbd className="bg-gray-100 px-2 py-1 rounded border border-gray-300 text-xs">
                                Space
                            </kbd>
                            <span>Xem nhanh</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <kbd className="bg-gray-100 px-2 py-1 rounded border border-gray-300 text-xs">
                                Esc
                            </kbd>
                            <span>Đóng</span>
                        </div>
                    </div>
                </div>

                {/* Right Panel: File Metadata */}
                <div className="lg:col-span-2">
                    <div className="bg-white rounded-xl border border-gray-200 p-6 sticky top-24 max-h-[calc(100vh-120px)] overflow-y-auto">
                        <FileMetadataPanel
                            selectedFolder={selectedFolder}
                            selectedDocument={selectedDocument}
                            onDownload={handleDownload}
                            onShare={handleShare}
                        />
                    </div>
                </div>
            </div>

            {/* Status Info */}
            {folders.length > 0 && (
                <div className="text-xs text-gray-500 text-center py-4">
                    Hiển thị {folders.length} thư mục gốc
                    {selectedFolder && ` • Đã chọn: ${selectedFolder.name}`}
                    {selectedDocument &&
                        ` • Tệp: ${selectedDocument.original_name || selectedDocument.filename}`}
                </div>
            )}
        </div>
    );
}
