'use client';

import React, { useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { PaperclipIcon, SendIcon, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
}

export function ChatInput({ onSend, isLoading = false }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSend(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSubmit(e as any);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setMessage(newValue);

    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        120
      )}px`;
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="sticky bottom-0 p-4 border-t border-border bg-background"
    >
      <div className="flex gap-3 items-end">
        <div className="flex-1 flex gap-2 items-end bg-card border border-input rounded-lg p-3">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="flex-shrink-0 text-muted-foreground hover:text-foreground"
            title="Attach file"
          >
            <PaperclipIcon className="w-5 h-5" />
          </Button>

          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask me anything..."
            className="flex-1 bg-transparent text-foreground placeholder:text-muted-foreground resize-none outline-none max-h-32 text-sm"
            rows={1}
          />
        </div>

        <Button
          type="submit"
          disabled={!message.trim() || isLoading}
          className="flex-shrink-0"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <SendIcon className="w-4 h-4" />
          )}
        </Button>
      </div>
      <p className="text-xs text-muted-foreground mt-2">
        Tip: Use Ctrl+Enter to send
      </p>
    </form>
  );
}
