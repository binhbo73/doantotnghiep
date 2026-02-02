'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { MessageCircle, Upload } from 'lucide-react';

interface EmptyStateProps {
  type: 'chat' | 'documents';
  onAction?: () => void;
}

export function EmptyState({ type, onAction }: EmptyStateProps) {
  if (type === 'chat') {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center">
        <div className="p-4 rounded-full bg-primary/10 mb-4">
          <MessageCircle className="w-8 h-8 text-primary" />
        </div>
        <h3 className="text-lg font-semibold mb-2">No conversations yet</h3>
        <p className="text-muted-foreground mb-6 max-w-sm">
          Start a new conversation by asking a question about your documents and
          knowledge base.
        </p>
        <Button onClick={onAction}>Start Chat</Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center h-96 text-center">
      <div className="p-4 rounded-full bg-primary/10 mb-4">
        <Upload className="w-8 h-8 text-primary" />
      </div>
      <h3 className="text-lg font-semibold mb-2">No documents uploaded</h3>
      <p className="text-muted-foreground mb-6 max-w-sm">
        Upload documents to build your knowledge base. Supported formats: PDF,
        DOCX, CSV, and TXT files.
      </p>
      <Button onClick={onAction}>Upload Documents</Button>
    </div>
  );
}
