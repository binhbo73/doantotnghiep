'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  FileText,
  FileJson,
  File,
  Trash2,
  RefreshCw,
  Search,
} from 'lucide-react';

interface DocumentFile {
  id: string;
  name: string;
  type: 'PDF' | 'DOCX' | 'CSV' | 'TXT';
  uploadDate: Date;
  status: 'Processing' | 'Ready' | 'Error';
  category: string;
  size: number;
}

interface FileTableProps {
  onDelete?: (id: string) => void;
  onReindex?: (id: string) => void;
}

const getFileIcon = (type: string) => {
  switch (type) {
    case 'PDF':
      return <FileText className="w-4 h-4 text-red-500" />;
    case 'DOCX':
      return <FileText className="w-4 h-4 text-blue-500" />;
    case 'CSV':
      return <FileJson className="w-4 h-4 text-green-500" />;
    default:
      return <File className="w-4 h-4 text-gray-500" />;
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'Ready':
      return 'bg-green-500/10 text-green-700 dark:text-green-400';
    case 'Processing':
      return 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400';
    case 'Error':
      return 'bg-red-500/10 text-red-700 dark:text-red-400';
    default:
      return 'bg-gray-500/10 text-gray-700 dark:text-gray-400';
  }
};

const mockDocuments: DocumentFile[] = [
  {
    id: '1',
    name: 'HR_Policy.pdf',
    type: 'PDF',
    uploadDate: new Date('2024-01-20'),
    status: 'Ready',
    category: 'HR',
    size: 2.4,
  },
  {
    id: '2',
    name: 'Employee_Handbook.docx',
    type: 'DOCX',
    uploadDate: new Date('2024-01-19'),
    status: 'Ready',
    category: 'HR',
    size: 1.8,
  },
  {
    id: '3',
    name: 'Product_Guide.pdf',
    type: 'PDF',
    uploadDate: new Date('2024-01-18'),
    status: 'Processing',
    category: 'Product',
    size: 5.2,
  },
  {
    id: '4',
    name: 'Training_Data.csv',
    type: 'CSV',
    uploadDate: new Date('2024-01-17'),
    status: 'Error',
    category: 'Training',
    size: 0.9,
  },
];

export function FileTable({ onDelete, onReindex }: FileTableProps) {
  const [documents, setDocuments] = useState<DocumentFile[]>(mockDocuments);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch =
      doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.category.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === 'all' || doc.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleDelete = (id: string) => {
    setDocuments(documents.filter((doc) => doc.id !== id));
    onDelete?.(id);
  };

  const handleReindex = (id: string) => {
    setDocuments(
      documents.map((doc) =>
        doc.id === id ? { ...doc, status: 'Processing' as const } : doc
      )
    );
    onReindex?.(id);
  };

  return (
    <div className="space-y-4">
      {/* Search and Filter */}
      <div className="flex flex-col gap-3 md:gap-4 md:flex-row md:items-center md:justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 text-sm"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-full md:w-40">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="Ready">Ready</SelectItem>
            <SelectItem value="Processing">Processing</SelectItem>
            <SelectItem value="Error">Error</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="overflow-x-auto text-sm md:text-base">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>File Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Upload Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Category</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredDocuments.length > 0 ? (
                filteredDocuments.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {getFileIcon(doc.type)}
                        <span className="font-medium truncate">{doc.name}</span>
                      </div>
                    </TableCell>
                    <TableCell>{doc.type}</TableCell>
                    <TableCell>
                      {doc.uploadDate.toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(doc.status)}>
                        {doc.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{doc.category}</TableCell>
                    <TableCell className="text-right space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleReindex(doc.id)}
                        title="Re-index document"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:text-destructive"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogTitle>Delete Document</AlertDialogTitle>
                          <AlertDialogDescription>
                            Are you sure you want to delete {doc.name}? This
                            action cannot be undone.
                          </AlertDialogDescription>
                          <div className="flex justify-end gap-3 mt-6">
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => handleDelete(doc.id)}
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            >
                              Delete
                            </AlertDialogAction>
                          </div>
                        </AlertDialogContent>
                      </AlertDialog>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8">
                    <p className="text-muted-foreground">No documents found</p>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
