'use client';

import React, { useState } from 'react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Copy, CheckCheck } from 'lucide-react';

interface Source {
  document: string;
  page: number;
  snippet: string;
}

interface MessageProps {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp: Date;
}

export function Message({ role, content, sources, timestamp }: MessageProps) {
  const [copied, setCopied] = useState(false);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isUser = role === 'user';

  return (
    <div className={`flex gap-3 mb-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <Avatar className="w-8 h-8 flex-shrink-0">
        {isUser ? (
          <>
            <AvatarFallback className="bg-primary text-primary-foreground">
              You
            </AvatarFallback>
          </>
        ) : (
          <>
            <AvatarFallback className="bg-sidebar-primary text-sidebar-primary-foreground">
              AI
            </AvatarFallback>
          </>
        )}
      </Avatar>

      <div className={`flex-1 max-w-2xl ${isUser ? 'text-right' : 'text-left'}`}>
        {/* Message Bubble */}
        <div
          className={`inline-block px-4 py-2 rounded-lg ${
            isUser
              ? 'bg-primary text-primary-foreground'
              : 'bg-card text-card-foreground border border-border'
          }`}
        >
          <p className="text-sm leading-relaxed break-words">{content}</p>

          {/* Copy Button for AI Messages */}
          {!isUser && (
            <div className="flex items-center justify-end mt-2 gap-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={copyToClipboard}
              >
                {copied ? (
                  <>
                    <CheckCheck className="w-3 h-3 mr-1" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3 mr-1" />
                    Copy
                  </>
                )}
              </Button>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <p className="text-xs text-muted-foreground mt-1">
          {timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>

        {/* Source Tags */}
        {sources && sources.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {sources.map((source, idx) => (
              <button
                key={idx}
                onClick={() =>
                  setSelectedSource(
                    selectedSource?.document === source.document ? null : source
                  )
                }
                className="group"
              >
                <Badge variant="secondary" className="text-xs">
                  {source.document}
                  {source.page > 0 && `, p.${source.page}`}
                </Badge>
              </button>
            ))}
          </div>
        )}

        {/* Source Preview */}
        {selectedSource && (
          <div className="mt-3 p-3 bg-muted rounded-lg border border-border text-xs">
            <p className="font-semibold mb-2 text-foreground">
              {selectedSource.document}
            </p>
            <p className="text-muted-foreground italic">
              &quot;{selectedSource.snippet}&quot;
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
