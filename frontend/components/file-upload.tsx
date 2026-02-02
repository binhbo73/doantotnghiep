'use client';

import React, { useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Upload, X } from 'lucide-react';

interface FileUploadProps {
  onUpload: (files: File[]) => void;
}

export function FileUpload({ onUpload }: FileUploadProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true);
    } else if (e.type === 'dragleave') {
      setIsDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    handleFiles(files);
  };

  const handleFiles = (files: File[]) => {
    setIsUploading(true);
    setUploadProgress(0);

    // Simulate file upload progress
    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsUploading(false);
          onUpload(files);
          return 100;
        }
        return prev + Math.random() * 30;
      });
    }, 300);
  };

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
        isDragActive
          ? 'border-primary bg-primary/5'
          : 'border-border hover:border-primary/50'
      }`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.csv,.txt"
        onChange={handleChange}
        className="hidden"
      />

      {isUploading ? (
        <div className="space-y-3">
          <div className="flex items-center justify-center gap-2">
            <div className="w-6 h-6 rounded-full border-2 border-transparent border-t-primary animate-spin" />
            <span className="text-sm font-medium">Uploading...</span>
          </div>
          <Progress value={uploadProgress} className="w-full" />
          <p className="text-xs text-muted-foreground">
            {Math.round(uploadProgress)}% complete
          </p>
        </div>
      ) : (
        <>
          <div className="flex justify-center mb-4">
            <div className="p-3 rounded-full bg-primary/10">
              <Upload className="w-6 h-6 text-primary" />
            </div>
          </div>
          <p className="font-semibold mb-1">Drag and drop files here</p>
          <p className="text-sm text-muted-foreground mb-4">
            or click to select files. Supported: PDF, DOCX, CSV, TXT
          </p>
          <Button
            type="button"
            onClick={() => inputRef.current?.click()}
          >
            Select Files
          </Button>
        </>
      )}
    </div>
  );
}
