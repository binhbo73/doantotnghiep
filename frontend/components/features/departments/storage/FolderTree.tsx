/**
 * Folder Tree Component
 * Displays hierarchical folder structure with files
 */

'use client';

import React from 'react';
import { ChevronRight, ChevronDown, Folder, FolderOpen, FileText, Archive, AlertCircle } from 'lucide-react';
import { FolderTreeNode, DocumentNode } from '@/hooks/departments/useDepartmentFolders';

interface FolderTreeProps {
    folders: FolderTreeNode[];
    selectedFolder: FolderTreeNode | null;
    selectedDocument: DocumentNode | null;
    onSelectFolder: (folder: FolderTreeNode) => void;
    onSelectDocument: (document: DocumentNode) => void;
    onToggleFolder: (folderId: string) => void;
}

function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 10) / 10 + ' ' + sizes[i];
}

function formatDate(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffHours < 1) return 'vừa xong';
    if (diffHours < 24) return diffHours + ' giờ trước';
    if (diffDays < 7) return diffDays + ' ngày trước';
    if (diffDays < 30) return Math.floor(diffDays / 7) + ' tuần trước';

    return date.toLocaleDateString('vi-VN');
}

function getFileIcon(fileType: string): React.ReactNode {
    const type = fileType.toLowerCase();
    if (type === 'zip' || type === 'rar' || type === 'compressed') {
        return <Archive className="w-4 h-4 text-blue-500" />;
    }
    return <FileText className="w-4 h-4 text-orange-500" />;
}

function getStatusBadge(status: string): React.ReactNode {
    const statusMap: Record<string, { label: string; bg: string; text: string }> = {
        completed: { label: 'Hoàn thành', bg: 'bg-green-100', text: 'text-green-700' },
        processing: { label: 'Đang xử lý', bg: 'bg-amber-100', text: 'text-amber-700' },
        pending: { label: 'Chờ xử lý', bg: 'bg-gray-100', text: 'text-gray-700' },
        failed: { label: 'Lỗi', bg: 'bg-red-100', text: 'text-red-700' },
    };

    const config = statusMap[status] || statusMap.pending;
    const dotColor: Record<string, string> = {
        completed: 'bg-green-500',
        processing: 'bg-amber-500',
        pending: 'bg-gray-500',
        failed: 'bg-red-500',
    };

    return (
        <div className={`flex items-center gap-1 ${config.bg} ${config.text} px-2 py-0.5 rounded-full text-[9px] font-bold uppercase`}>
            <span className={`w-1.5 h-1.5 ${dotColor[status]} rounded-full`}></span>
            {config.label}
        </div>
    );
}

export function FolderTree({
    folders,
    selectedFolder,
    selectedDocument,
    onSelectFolder,
    onSelectDocument,
    onToggleFolder,
}: FolderTreeProps) {
    return (
        <div className="flex flex-col gap-1">
            {folders.map((folder) => (
                <FolderTreeNodeComponent
                    key={folder.id}
                    folder={folder}
                    level={0}
                    isSelectedFolder={selectedFolder?.id === folder.id}
                    isSelectedDocument={selectedDocument !== null}
                    onSelectFolder={onSelectFolder}
                    onSelectDocument={onSelectDocument}
                    onToggleFolder={onToggleFolder}
                />
            ))}
        </div>
    );
}

interface FolderTreeNodeComponentProps {
    folder: FolderTreeNode;
    level: number;
    isSelectedFolder: boolean;
    isSelectedDocument: boolean;
    onSelectFolder: (folder: FolderTreeNode) => void;
    onSelectDocument: (document: DocumentNode) => void;
    onToggleFolder: (folderId: string) => void;
}

function FolderTreeNodeComponent({
    folder,
    level,
    isSelectedFolder,
    isSelectedDocument,
    onSelectFolder,
    onSelectDocument,
    onToggleFolder,
}: FolderTreeNodeComponentProps) {
    const hasSubfolders = folder.subFolders.length > 0;
    const hasDocuments = folder.documents.length > 0;
    const hasChildren = hasSubfolders || hasDocuments;
    const marginLeft = `${level * 24}px`;

    const handleToggle = (e: React.MouseEvent) => {
        e.stopPropagation();
        onToggleFolder(folder.id);
    };

    return (
        <div>
            {/* Folder Item */}
            <div
                onClick={() => onSelectFolder(folder)}
                className={`flex items-center gap-2 py-2 px-3 rounded-lg cursor-pointer transition-all ${isSelectedFolder
                        ? 'bg-blue-50 text-blue-700'
                        : 'hover:bg-gray-100 text-gray-700'
                    }`}
                style={{ marginLeft }}
            >
                {/* Expand/Collapse Icon */}
                {hasChildren ? (
                    <button
                        onClick={handleToggle}
                        className="p-0.5 hover:bg-gray-200 rounded transition-colors flex-shrink-0"
                    >
                        {folder.expanded ? (
                            <ChevronDown className="w-4 h-4" />
                        ) : (
                            <ChevronRight className="w-4 h-4" />
                        )}
                    </button>
                ) : (
                    <div className="w-5" />
                )}

                {/* Folder Icon */}
                {folder.expanded && hasChildren ? (
                    <FolderOpen className="w-4 h-4 text-orange-400 flex-shrink-0" />
                ) : (
                    <Folder className="w-4 h-4 text-orange-400 flex-shrink-0" />
                )}

                {/* Folder Name */}
                <span className="text-sm font-semibold flex-1 truncate">
                    {folder.name}
                </span>

                {/* File Count Badge */}
                <span className="text-[10px] text-gray-500 font-mono ml-auto flex-shrink-0">
                    {folder.totalFiles || 0} FILES
                </span>
            </div>

            {/* Documents and Subfolders */}
            {folder.expanded && hasChildren && (
                <div className="relative">
                    {/* Connector Line */}
                    <div
                        className="absolute left-0 top-0 bottom-0 w-px bg-gray-200"
                        style={{ left: `${level * 24 + 12}px` }}
                    />

                    {/* Subfolders */}
                    {hasSubfolders && (
                        <div>
                            {folder.subFolders.map((subfolder) => (
                                <FolderTreeNodeComponent
                                    key={subfolder.id}
                                    folder={subfolder}
                                    level={level + 1}
                                    isSelectedFolder={false}
                                    isSelectedDocument={false}
                                    onSelectFolder={onSelectFolder}
                                    onSelectDocument={onSelectDocument}
                                    onToggleFolder={onToggleFolder}
                                />
                            ))}
                        </div>
                    )}

                    {/* Documents */}
                    {hasDocuments && (
                        <div>
                            {folder.documents.map((doc) => (
                                <DocumentItemComponent
                                    key={doc.id}
                                    document={doc}
                                    level={level + 1}
                                    onSelectDocument={onSelectDocument}
                                />
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

interface DocumentItemComponentProps {
    document: DocumentNode;
    level: number;
    onSelectDocument: (document: DocumentNode) => void;
}

function DocumentItemComponent({
    document,
    level,
    onSelectDocument,
}: DocumentItemComponentProps) {
    const marginLeft = `${level * 24}px`;

    return (
        <div
            onClick={() => onSelectDocument(document)}
            className="flex items-center gap-2 py-2 px-3 rounded-lg cursor-pointer transition-all hover:bg-orange-50"
            style={{ marginLeft }}
        >
            {/* Spacer for indent */}
            <div className="w-5" />

            {/* File Icon */}
            {getFileIcon(document.file_type)}

            {/* Document Details */}
            <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 truncate">
                    {document.original_name || document.filename}
                </div>
                <div className="flex items-center gap-3 text-[10px] text-gray-500 mt-1">
                    <span>{formatFileSize(document.file_size)}</span>
                    <span>•</span>
                    <span>Cập nhật: {formatDate(document.updated_at)}</span>
                </div>
            </div>

            {/* Status Badge */}
            <div className="flex-shrink-0">
                {getStatusBadge(document.status)}
            </div>
        </div>
    );
}
